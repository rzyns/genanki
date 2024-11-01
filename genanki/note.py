from collections.abc import Iterable
import re
from typing import Any, Generic, SupportsIndex, TypeVar

import attr
from attrs import define, field

from anki import notes_pb2

from genanki.util import guid_for
from genanki.model import FieldSpec, VirtualModel, RealizedModel, ModelSpec, ModelType
from genanki.card import Card


class Tag:
    _tag: str

    def __init__(self, tag: str):
        self._tag = self._validate_tag(tag)

    def __contains__(self, key: str, /) -> bool:
        return self._tag.__contains__(key)

    @staticmethod
    def _validate_tag(tag: str):
        if " " in tag:
            raise ValueError(f'Tag "{tag}" contains a space; this is not allowed!')
        return tag


class _TagList(list[Tag]):
    tags: list[Tag]

    @staticmethod
    def _validate_tag(tag: Tag):
        if " " in tag:
            raise ValueError(f'Tag "{tag}" contains a space; this is not allowed!')

    def __init__(self, tags: Iterable[Tag | str] = ()):
        super().__init__()
        self.extend(x if isinstance(x, Tag) else Tag(x) for x in tags)

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"

    def __setitem__(self, key: slice | SupportsIndex, val: Tag | str | Iterable[Tag | str]):
        if isinstance(val, str):
            Tag._validate_tag(val)

        if isinstance(key, SupportsIndex) and isinstance(val, Tag):
            self._validate_tag(val)
            super().__setitem__(key, val)
        elif isinstance(key, slice):
            # val may be an iterator, convert to a list so we can iterate multiple times
            _val: list[Tag]
            # list(val) if isinstance(val, Iterable) else [val]
            if isinstance(val, str):
                _val = [Tag(val)]
            elif isinstance(val, Tag):
                _val = [val]
            else:
                _val = [Tag(x) if isinstance(x, str) else x for x in val]

            for tag in _val:
                self._validate_tag(tag)

            super().__setitem__(key, _val)

    def append(self, tag: str | Tag):
        t = tag if isinstance(tag, Tag) else Tag(tag)
        self._validate_tag(t)
        super().append(t)

    def extend(self, tags: Iterable[Tag | str]):
        # tags may be an iterator, convert to list so we can iterate multiple times
        tags = [Tag(tag) if isinstance(tag, str) else tag for tag in tags]
        for tag in tags:
            self._validate_tag(tag)
        super().extend(tags)

    def insert(self, i: SupportsIndex, tag: Tag | str):
        t = tag if isinstance(tag, Tag) else Tag(tag)
        self._validate_tag(t)
        super().insert(i, t)


def _validate_sort_field[F: FieldSpec](self: "VirtualNote[F]", _attr: "attr.Attribute[str]", val: str) -> bool:
    return val in list(map(lambda x: x["name"], self.model.fields))

def _default_sort_field[F: FieldSpec](self: "VirtualNote[F]") -> str:
    return self.model.fields[0]["name"]


F_co = TypeVar("F_co", bound=FieldSpec, covariant=True, default=FieldSpec)


@define(kw_only=True, slots=True)
class VirtualNote(Generic[F_co]):
    model: VirtualModel[ModelSpec[F_co]] = field()
    fields: F_co = field()
    due: int = field(default=0)

    _INVALID_HTML_TAG_RE = re.compile(
        r"<(?!/?[a-zA-Z0-9]+(?: .*|/?)>|!--|!\[CDATA\[)(?:.|\n)*?>"
    )

    sort_field: str = field(validator=_validate_sort_field, default=attr.Factory(_default_sort_field, takes_self=True))
    _cards: list[Card] | None = field(default=None)
    _tags: _TagList = field(factory=_TagList, alias="tags", converter=_TagList)

    _guid: str | None = field(default=None, alias="guid")

    @property
    def guid(self) -> str:
        if self._guid is not None:
            return self._guid
        return guid_for(self.fields)

    def __attrs_post_init__(self):
        if not hasattr(self.__class__, "guid") or self.__class__.guid.__isabstractmethod__:
            raise NotImplementedError("Must implement guid property")

        self._check_number_model_fields_matches_num_fields()
        self._check_invalid_html_tags_in_fields()

    @property
    def tags(self) -> _TagList:
        return self._tags

    @tags.setter
    def tags(self, val: Iterable[Tag | str]):
        self._tags = _TagList()
        self._tags.extend(x if isinstance(x, Tag) else Tag(x) for x in val)

    @property
    def cards(self) -> list[Card]:
        if self._cards is None:
            if self.model.model_type == ModelType.FRONT_BACK:
                self._cards = self._front_back_cards()
            elif self.model.model_type == ModelType.CLOZE:
                self._cards = self._cloze_cards()
            else:
                raise ValueError("Expected model_type CLOZE or FRONT_BACK")

        return self._cards

    def write_to_db(self, a: Any, b: Any, c: Any, d: Any):
        pass

    @property
    def req(self) -> notes_pb2.Note:
        result = notes_pb2.Note(
            fields=self.fields.values(),
            guid=self.guid,
            # id=,
            # mtime_secs=,
            notetype_id=self.model.model_id or 0,
            # tags=,
            # usn=,
        )
        return result

    def _cloze_cards(self) -> list[Card]:
        """Returns a Card with unique ord for each unique cloze reference."""
        card_ords: set[int] = set()
        # find cloze replacements in first template's qfmt, e.g "{{cloze::Text}}"
        cloze_replacements = set(
            re.findall(
                r"{{[^}]*?cloze:(?:[^}]?:)*(.+?)}}", self.model.templates[0]["qfmt"]
            )
            + re.findall("<%cloze:(.+?)%>", self.model.templates[0]["qfmt"])
        )
        for field_name in cloze_replacements:
            field_index = next(
                (i for i, f in enumerate(self.model.fields) if f["name"] == field_name),
                -1,
            )
            field_value = self.fields.values()[field_index] if field_index >= 0 else ""
            # update card_ords with each cloze reference N, e.g. "{{cN::...}}"
            card_ords.update(
                m - 1
                for m in map(
                    int, re.findall(r"{{c(\d+)::.+?}}", field_value, re.DOTALL)
                )
                if m > 0
            )
        if card_ords == set():
            card_ords = {0}
        return [Card(ord_) for ord_ in card_ords]

    def _front_back_cards(self) -> list[Card]:
        """Create Front/Back cards"""
        rv: list[Card] = []

        for card_ord, any_or_all, required_field_ords in self.model._req:
            op = {"any": any, "all": all}[any_or_all]
            if op(self.fields.defs()[ord_] for ord_ in required_field_ords):
                rv.append(Card(card_ord))
        return rv


    def _check_number_model_fields_matches_num_fields(self) -> None:
        if len(self.model.fields) != len(self.fields.defs()):
            raise ValueError(
                "Number of fields in Model does not match number of fields in Note: "
                f"{self.model} has {len(self.model.fields)} fields, but {self} has {len(self.fields.defs())} fields."
            )

    @classmethod
    def _find_invalid_html_tags_in_field(cls, field: str):
        return cls._INVALID_HTML_TAG_RE.findall(field)

    def _check_invalid_html_tags_in_fields(self):
        for _idx, field_ in enumerate(self.fields.values()):
            invalid_tags = self._find_invalid_html_tags_in_field(field_)
            if invalid_tags:
                # You can disable the below warning by calling warnings.filterwarnings:
                #
                # warnings.filterwarnings('ignore', module='genanki', message='^Field contained the following invalid HTML tags')
                #
                # If you think you're getting a false positive for this warning, please file an issue at
                # https://github.com/kerrickstaley/genanki/issues
                raise ValueError(
                    "Field contained the following invalid HTML tags. Make sure you are calling html.escape() if"
                    " your field data isn't already HTML-encoded: {}".format(
                        " ".join(invalid_tags)
                    ),
                )

    def _format_fields(self):
        return "\x1f".join(self.fields.values())

    def _format_tags(self) -> str:
        return f" {" ".join(map(str, self.tags))} "

    def __repr__(self):
        attrs = ["model", "fields", "sort_field", "tags"]
        pieces = [f"{attr}={getattr(self, attr)!r}" for attr in attrs]
        return f"{self.__class__.__name__}({", ".join(pieces)})"


@define(kw_only=True, slots=True)
class RealizedNote(Generic[F_co]):
    pass
