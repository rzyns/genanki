from typing import Literal, Required, TypedDict

import anki
import anki.collection
import anki.decks
import anki.models

import chevron
import yaml
import pydantic


class Field(TypedDict, total=False):
    name: Required[str]
    ord: int
    font: str | None
    media: list[str]
    rtl: bool
    size: int
    sticky: bool


FieldAdapter = pydantic.TypeAdapter(Field)


class Template(TypedDict, total=False):
    name: str
    afmt: str
    qfmt: Required[str]
    ord: int
    bafmt: str
    bqfmt: str
    bfont: str
    bsize: int
    did: anki.decks.DeckId | None


TemplateAdapter = pydantic.TypeAdapter(Template)


type _Req = list[
    tuple[int, Literal["all"], list[int]] | tuple[int, Literal["any"], list[int]]
]


class ModelDict(TypedDict):
    css: str
    did: anki.decks.DeckId
    flds: list[Field]
    id: anki.models.NotetypeId
    latexPost: str
    latexPre: str
    latexsvg: bool
    mod: int
    name: str
    req: _Req
    sortf: int
    tags: list[str]
    tmpls: list[Template]
    type: int
    usn: int
    vers: list[str]


ModelDictAdapter = pydantic.TypeAdapter(ModelDict)


FieldOrStr = str | Field
TemplateOrStr = dict[str, str] | Template


class Model:
    FRONT_BACK: int = 0
    CLOZE: int = 1
    DEFAULT_LATEX_PRE: str = (
        "\\documentclass[12pt]{article}\n\\special{papersize=3in,5in}\n\\usepackage[utf8]{inputenc}\n"
        "\\usepackage{amssymb,amsmath}\n\\pagestyle{empty}\n\\setlength{\\parindent}{0in}\n"
        "\\begin{document}\n"
    )
    DEFAULT_LATEX_POST = "\\end{document}"

    fields: list[Field]
    templates: list[Template]
    model_type: int

    def __init__(
        self,
        model_id: int | None = None,
        name: str | None = None,
        fields: str | list[FieldOrStr] | None = None,
        templates: list[TemplateOrStr] | None = None,
        css: str = "",
        model_type: int = FRONT_BACK,
        latex_pre: str = DEFAULT_LATEX_PRE,
        latex_post: str = DEFAULT_LATEX_POST,
        sort_field_index: int = 0,
    ):
        self.model_id = model_id
        self.name = name
        self.set_fields(fields)
        self.set_templates(templates)
        self.css = css
        self.model_type = model_type
        self.latex_pre = latex_pre
        self.latex_post = latex_post
        self.sort_field_index = sort_field_index

    def set_fields(self, fields: str | list[FieldOrStr] | None):
        if isinstance(fields, list):
            self.fields = [FieldAdapter.validate_python(field) for field in fields]
        elif isinstance(fields, str):
            self.fields = pydantic.TypeAdapter(list[Field]).validate_python(
                yaml.full_load(fields)
            )

    def set_templates(self, templates: str | list[TemplateOrStr] | None):
        if isinstance(templates, list):
            self.templates = [
                TemplateAdapter.validate_python(template) for template in templates
            ]
        elif isinstance(templates, str):
            self.templates = pydantic.TypeAdapter(list[Template]).validate_python(
                yaml.full_load(templates)
            )

    @property
    def req(self) -> _Req:
        return self._req

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
        field_names = [field["name"] for field in self.fields]

        req: _Req = []
        for template_ord, template in enumerate(self.templates):
            required_fields: list[int] = []
            for field_ord, field in enumerate(field_names):
                field_values = dict.fromkeys(field_names, sentinel)
                field_values[field] = ""

                rendered = chevron.render(template["qfmt"], field_values)

                if sentinel not in rendered:
                    # when this field is missing, there is no meaningful content (no field values) in the question, so this field
                    # is required
                    required_fields.append(field_ord)

            if required_fields:
                req.append((template_ord, "all", required_fields))
                continue

            # there are no required fields, so an "all" is not appropriate, switch to checking for "any"
            for field_ord, field in enumerate(field_names):
                field_values = dict.fromkeys(field_names, "")
                field_values[field] = sentinel

                rendered = chevron.render(template["qfmt"], field_values)

                if sentinel in rendered:
                    # when this field is present, there is meaningful content in the question
                    required_fields.append(field_ord)

            if not required_fields:
                raise Exception(
                    f'Could not compute required fields for this template; please check the formatting of "qfmt": {template}'
                )

            req.append((template_ord, "any", required_fields))

        return req

    def to_json(self, timestamp: float, deck_id: anki.decks.DeckId):
        for ord_, tmpl in enumerate(self.templates):
            tmpl["ord"] = ord_
            tmpl.setdefault("bafmt", "")
            tmpl.setdefault("bqfmt", "")
            tmpl.setdefault("bfont", "")
            tmpl.setdefault("bsize", 0)
            tmpl.setdefault(
                "did", None
            )  # TODO None works just fine here, but should it be deck_id?

        for ord_, field in enumerate(self.fields):
            field["ord"] = ord_
            field.setdefault("font", "Liberation Sans")
            field.setdefault("media", [])
            field.setdefault("rtl", False)
            field.setdefault("size", 20)
            field.setdefault("sticky", False)

        return ModelDictAdapter.validate_python(
            {
                "css": self.css,
                "did": deck_id,
                "flds": self.fields,
                "id": str(self.model_id),
                "latexPost": self.latex_post,
                "latexPre": self.latex_pre,
                "latexsvg": False,
                "mod": int(timestamp),
                "name": self.name,
                "req": self._req,
                "sortf": self.sort_field_index,
                "tags": [],
                "tmpls": self.templates,
                "type": self.model_type,
                "usn": -1,
                "vers": [],
            }
        )

    def __repr__(self):
        attrs = ["model_id", "name", "fields", "templates", "css", "model_type"]
        pieces = [f"{attr}={getattr(self, attr)!r}" for attr in attrs]
        return "{}({})".format(self.__class__.__name__, ", ".join(pieces))
