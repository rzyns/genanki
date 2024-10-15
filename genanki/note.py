from collections.abc import Iterable
import re
from typing import Protocol, SupportsIndex
from .model import Model
from sqlite3 import Cursor

from .builtin_models import _fix_deprecated_builtin_models_and_warn
from .card import Card
from .util import guid_for


class SupportsNext[T](Protocol):
    def __next__(self) -> T: ...


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


class Note:
    _INVALID_HTML_TAG_RE = re.compile(
        r"<(?!/?[a-zA-Z0-9]+(?: .*|/?)>|!--|!\[CDATA\[)(?:.|\n)*?>"
    )

    _sort_field: str | None
    _guid: str | None
    _cards: list[Card] | None

    def __init__(
        self,
        model: Model | None = None,
        fields: list[str] | None = None,
        sort_field: str | None = None,
        tags: list[str] | None = None,
        guid: str | None = None,
        due: int = 0,
    ):
        self.model = model or Model()
        self.fields = fields or []
        self.sort_field = sort_field
        self.tags = _TagList(tags or [])
        self.due = due
        self._guid = None
        self._cards = None

        if guid is not None:
            try:  # noqa: SIM105
                self.guid = guid
            except AttributeError:
                # guid was defined as a property
                pass

    @property
    def sort_field(self) -> str | None:
        if self._sort_field is not None:
            return self._sort_field
        else:
            return self.fields[self.model.sort_field_index]

    @sort_field.setter
    def sort_field(self, val: str | None):
        self._sort_field = val

    @property
    def tags(self) -> _TagList:
        return self._tags

    @tags.setter
    def tags(self, val: Iterable[Tag | str]):
        self._tags = _TagList()
        self._tags.extend(x if isinstance(x, Tag) else Tag(x) for x in val)

    # We use cached_property instead of initializing in the constructor so that the user can set the model after calling
    # __init__ and it'll still work.
    @property
    def cards(self) -> list[Card]:
        if self._cards is None:
            if self.model.model_type == self.model.FRONT_BACK:
                self._cards = self._front_back_cards()
            elif self.model.model_type == self.model.CLOZE:
                self._cards = self._cloze_cards()
            else:
                raise ValueError("Expected model_type CLOZE or FRONT_BACK")

        return self._cards

    def _cloze_cards(self):
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
            field_value = self.fields[field_index] if field_index >= 0 else ""
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

    def _front_back_cards(self):
        """Create Front/Back cards"""
        rv: list[Card] = []
        for card_ord, any_or_all, required_field_ords in self.model.req:
            op = {"any": any, "all": all}[any_or_all]
            if op(self.fields[ord_] for ord_ in required_field_ords):
                rv.append(Card(card_ord))
        return rv

    @property
    def guid(self):
        if self._guid is None:
            self._guid = guid_for(*self.fields)
        return self._guid

    @guid.setter
    def guid(self, val: str):
        self._guid = val

    def _check_number_model_fields_matches_num_fields(self):
        if len(self.model.fields) != len(self.fields):
            raise ValueError(
                "Number of fields in Model does not match number of fields in Note: "
                f"{self.model} has {len(self.model.fields)} fields, but {self} has {len(self.fields)} fields."
            )

    @classmethod
    def _find_invalid_html_tags_in_field(cls, field: str):
        return cls._INVALID_HTML_TAG_RE.findall(field)

    def _check_invalid_html_tags_in_fields(self):
        for _idx, field in enumerate(self.fields):
            invalid_tags = self._find_invalid_html_tags_in_field(field)
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

    def write_to_db[T](
        self, cursor: Cursor, timestamp: float, deck_id: int, id_gen: SupportsNext[T]
    ):
        self.fields = _fix_deprecated_builtin_models_and_warn(self.model, self.fields)
        self._check_number_model_fields_matches_num_fields()
        self._check_invalid_html_tags_in_fields()

        params = (
            next(id_gen),           # id
            self.guid,              # guid
            self.model.model_id,    # mid
            int(timestamp),         # mod
            -1,                     # usn
            self._format_tags(),    # TODO tags
            self._format_fields(),  # flds
            self.sort_field,        # sfld
            0,                      # csum, can be ignored
            0,                      # flags
            "",                     # data
        )
        cursor.execute(
            "INSERT INTO notes VALUES(?,?,?,?,?,?,?,?,?,?,?);",
            params,
        )

        note_id = cursor.lastrowid
        if note_id is not None:
            for card in self.cards:
                card.write_to_db(cursor, timestamp, deck_id, note_id, id_gen, self.due)
        else:
            raise ValueError("Failed to insert note into database")

    def _format_fields(self):
        return "\x1f".join(self.fields)

    def _format_tags(self) -> str:
        return f" {" ".join(map(str, self.tags))} "

    def __repr__(self):
        attrs = ["model", "fields", "sort_field", "tags", "guid"]
        pieces = [f"{attr}={getattr(self, attr)!r}" for attr in attrs]
        return "{}({})".format(self.__class__.__name__, ", ".join(pieces))
