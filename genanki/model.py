from collections.abc import Sequence
import dataclasses
from enum import Enum
from typing import Any, Generic, Literal, NotRequired, TypeVar, TypedDict, dataclass_transform

from pydantic import TypeAdapter, ValidationError

import anki
import anki.collection
import anki.decks
import anki.models

from anki.generic_pb2 import UInt32
from anki import notetypes_pb2

import attrs


class ModelType(int, Enum):
    FRONT_BACK = 0
    CLOZE = 1


class UnnamedFieldData(TypedDict):
    ord: int
    font: str | None
    media: list[str]
    rtl: bool
    size: int
    sticky: bool


class FieldData(UnnamedFieldData):
    name: str


class UnnamedTemplateData(TypedDict):
    afmt: str
    qfmt: str
    ord: int
    bafmt: str
    bqfmt: str
    bfont: str
    bsize: int
    did: anki.decks.DeckId | None


class PartialUnnamedTemplateData(TypedDict, total=False):
    afmt: str
    qfmt: str
    ord: int
    bafmt: str
    bqfmt: str
    bfont: str
    bsize: int
    did: anki.decks.DeckId | None


class TemplateData(UnnamedTemplateData):
    name: str


type _Req = list[
    tuple[int, Literal["all"], list[int]]
    | tuple[int, Literal["any"], list[int]]
]


class ModelDict(TypedDict):
    css: str
    did: anki.decks.DeckId
    flds: list[FieldData]
    id: NotRequired[anki.models.NotetypeId]
    latexPost: str
    latexPre: str
    latexsvg: bool
    mod: int
    name: str
    req: _Req
    sortf: int
    tags: list[str]
    tmpls: list[TemplateData]
    type: int
    usn: int
    vers: list[str]


FieldOrStr = str | FieldData
TemplateOrStr = dict[str, str] | TemplateData


class ModelField(dataclasses.Field[str]):

    __genanki_field__: FieldData

    alias: str | None = None

    def __init__(self, data: UnnamedFieldData, *, alias: str | None = None, default: str | None = None) -> None:
        super().__init__(
            default=default if default is not None else "",
            default_factory=lambda: "",
            init=True,
            repr=True,
            hash=True,
            compare=True,
            metadata={},
            kw_only=True,
        )

        self.__genanki_field__ = { "name": "", **data }

        if alias:
            self.alias = alias


def field(field_data: UnnamedFieldData | None = None, *, alias: str | None = None, default: str | None = None) -> Any:
    if field_data is None:
        return ModelField(UnnamedFieldData(
            font="Arial",
            media=[],
            ord=0,
            rtl=False,
            size=20,
            sticky=False,
        ), alias=alias, default=default)
    return ModelField(field_data, alias=alias, default=default)


class ModelTemplate(dataclasses.Field[str]):
    __genanki_template__: TemplateData

    alias: str | None = None

    def __init__(self, data: UnnamedTemplateData, *, alias: str | None = None) -> None:
        super().__init__(
            default="",
            default_factory=lambda: "",
            init=True,
            repr=True,
            hash=True,
            compare=True,
            metadata={},
            kw_only=True,
        )

        self.__genanki_template__ = { "name": "", **data }

        if alias is not None:
            self.alias = alias


def template(template_data: PartialUnnamedTemplateData, *, alias: str | None = None) -> Any:
    try:
        data = TypeAdapter(UnnamedTemplateData).validate_python(template_data)

        return ModelTemplate(
            data,
            alias=alias,
        )
    except ValidationError:
        return ModelTemplate(
            UnnamedTemplateData(
                afmt=template_data.get("afmt", ""),
                qfmt=template_data.get("qfmt", ""),
                ord=template_data.get("ord", 0),
                bafmt=template_data.get("bafmt", ""),
                bqfmt=template_data.get("bqfmt", ""),
                bfont=template_data.get("bfont", ""),
                bsize=template_data.get("bsize", 20),
                did=template_data.get("did", anki.decks.DeckId(0)),
            ),
            alias=alias,
        )


@dataclasses.dataclass
class FieldSpec:
    def values(self) -> tuple[str, ...]:
        return dataclasses.astuple(self)

    @classmethod
    def defs(cls) -> Sequence[FieldData]:
        if not dataclasses.is_dataclass(cls):
            raise TypeError(f"{cls} is not a dataclass")

        flds: list[FieldData] = []

        for v in dataclasses.fields(cls):
            if isinstance(v, ModelField):
                flds.append(v.__genanki_field__)

        return flds

@dataclasses.dataclass
class TemplateSpec[T: FieldSpec]:
    fields: type[T]

    def __init_subclass__(cls, fields: type[T]) -> None:
        cls.fields = fields

    @classmethod
    def templates(cls) -> Sequence[TemplateData]:
        if not dataclasses.is_dataclass(cls):
            raise TypeError(f"{cls} is not a dataclass")

        tpls: list[TemplateData] = []

        for v in dataclasses.fields(cls):
            if isinstance(v, ModelTemplate):
                tpls.append(v.__genanki_template__)

        return tpls

T_co = TypeVar("T_co", bound=FieldSpec, contravariant=True, default=FieldSpec)
class ModelSpec(Generic[T_co]):
    fields: type[T_co]
    templates: type[TemplateSpec[T_co]]


@dataclass_transform(field_specifiers=(ModelField, field, ModelTemplate, template), kw_only_default=True)
def spec[T: ModelSpec[Any]](cls: type[T]) -> type[T]:
    new_cls = dataclasses.dataclass(cls)

    if dataclasses.is_dataclass(new_cls):
        for k, v in new_cls.__dataclass_fields__.items():
            if isinstance(v, ModelField):
                v.__genanki_field__["name"] = k if v.alias is None else v.alias
            elif isinstance(v, ModelTemplate):
                v.__genanki_template__["name"] = k

    return new_cls


M_co = TypeVar("M_co", bound=ModelSpec[FieldSpec], covariant=True, default=ModelSpec[FieldSpec])
# F_co = TypeVar("F_co", bound=FieldSpec, covariant=True, default=FieldSpec)

@attrs.define
class VirtualModel(Generic[M_co]):
    name: str = attrs.field(kw_only=True)
    did: anki.decks.DeckId = attrs.field(kw_only=True, converter=anki.decks.DeckId, default=anki.decks.DeckId(0))
    model_spec: type[M_co] = attrs.field(kw_only=True)

    css: str = attrs.field(default="", kw_only=True)
    latex_post: str = attrs.field(default="", kw_only=True)
    latex_pre: str = attrs.field(default="", kw_only=True)
    model_type: ModelType = attrs.field(default=ModelType.FRONT_BACK, kw_only=True)

    _sort_field_index: int | None = attrs.field(default=None, alias="sort_field_index", kw_only=True)

    @property
    def fields(self) -> Sequence[FieldData]:

        fields: list[FieldData] = []

        for f in dataclasses.fields(self.model_spec.fields):
            if isinstance(f, ModelField):
                fields.append(f.__genanki_field__)

        return fields

    @property
    def templates(self) -> Sequence[TemplateData]:
        return self.model_spec.templates.templates()

    def render(self, string: str, data: dict[str, str] | None = None) -> str:
        return string

    @property
    def sort_field_index(self) -> int:
        return self._sort_field_index if self._sort_field_index is not None else 0

    @property
    def req(self) -> notetypes_pb2.Notetype:
        return notetypes_pb2.Notetype(
            # config={},
            fields=[
                notetypes_pb2.Notetype.Field(
                    config=notetypes_pb2.Notetype.Field.Config(
                        collapsed=False,
                        description=f["name"],
                        exclude_from_search=False,
                        font_name=f["font"] or "Arial",
                        font_size=f["size"],
                        prevent_deletion=False,
                        rtl=False,
                        sticky=f["sticky"],
                    ),
                    name=f["name"],
                    ord=UInt32(val=f["ord"]),
                )
                for f in self.fields
            ],
            # id=,
            # mtime_secs=,
            name=self.name,
            templates=[
                notetypes_pb2.Notetype.Template(
                    config=notetypes_pb2.Notetype.Template.Config(
                        a_format=t["afmt"],
                        a_format_browser=t["bafmt"],
                        browser_font_name=t["bfont"],
                        browser_font_size=t["bsize"],
                        q_format=t["qfmt"],
                        q_format_browser=t["bqfmt"],
                    ),
                    name=t["name"],
                    ord=UInt32(val=t["ord"]),
                )
                for t in self.templates
            ],
            # usn=,
        )

    @property
    def _req(self) -> _Req:
        """
        List of required fields for each template. Format is [tmpl_idx, "all"|"any", [req_field_1, req_field_2, ...]].

        Partial reimplementation of req computing logic from Anki. We use chevron instead of Anki's custom mustache
        implementation.

        The goal is to figure out which fields are "required", i.e. if they are missing then the front side of the note
        doesn't contain any meaningful content.
        """
        sentinel = "SeNtInEl"
        field_names = [a.name for a in dataclasses.fields(self.model_spec.fields)]

        req: _Req = []
        for template_ord, template in enumerate(self.model_spec.templates.templates()):
            required_fields: list[int] = []
            for field_ord, field_ in enumerate(field_names):
                field_values = dict.fromkeys(field_names, sentinel)
                field_values[field_] = ""

                rendered = self.render(template["qfmt"], field_values)

                if sentinel not in rendered:
                    # when this field is missing, there is no meaningful content (no field values) in the question, so this field
                    # is required
                    required_fields.append(field_ord)

            if required_fields:
                req.append((template_ord, "all", required_fields))
                continue

            # there are no required fields, so an "all" is not appropriate, switch to checking for "any"
            for field_ord, field_ in enumerate(field_names):
                field_values = dict.fromkeys(field_names, "")
                field_values[field_] = sentinel

                rendered = self.render(template["qfmt"], field_values)

                if sentinel in rendered:
                    # when this field is present, there is meaningful content in the question
                    required_fields.append(field_ord)

            if not required_fields:
                raise Exception(
                    f'Could not compute required fields for this template; please check the formatting of "qfmt": {template}'
                )

            req.append((template_ord, "any", required_fields))

        return req


    def to_json(self, timestamp: float, deck_id: anki.decks.DeckId) -> ModelDict:
        data: ModelDict = {
            "css": self.css,
            "did": deck_id,
            "flds": list(self.fields),
            "latexPost": self.latex_post,
            "latexPre": self.latex_pre,
            "latexsvg": False,
            "mod": int(timestamp),
            "name": self.name,
            "req": self._req,
            "sortf": self.sort_field_index,
            "tags": [],
            "tmpls": list(self.model_spec.templates.templates()),
            "type": self.model_type,
            "usn": -1,
            "vers": [],
        }

        return data


@attrs.define(kw_only=True)
class RealizedModel(VirtualModel[M_co]):
    model_id: anki.models.NotetypeId = attrs.field()
