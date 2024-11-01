"""
Models that behave the same as Anki's built-in models ("Basic", "Basic (and reversed card)", "Cloze", etc.).

Note: Anki does not assign consistent IDs to its built-in models (see
    https://github.com/kerrickstaley/genanki/issues/55#issuecomment-717687667 and
    https://forums.ankiweb.net/t/exported-basic-cards-create-duplicate-card-types-when-imported-by-other-users/959 ).
    Because of this, we cannot simply call these models "Basic" etc. If we did, then when importing a genanki-generated
    deck, Anki would see a model called "Basic" which has a different model ID than its internal "Basic" model, and it
    would rename the imported model to something like "Basic-123abc". Instead, we name the models "Basic (genanki)"
    etc., which is less confusing.
"""

from typing import Any
import warnings

from genanki import model


class BasicModelSpec(model.ModelSpec[Any]):
    @model.spec
    class fields(model.FieldSpec):
        Front: str = model.field()
        Back: str = model.field()

    @model.spec
    class templates(model.TemplateSpec[fields], fields=fields):
        card_1: str = model.template({
            "qfmt": "{{Front}}",
            "afmt": "{{FrontSide}}\n\n<hr id=answer>\n\n{{Back}}",
        })

BASIC_MODEL = model.Model(
    name="Basic (genanki)",
    model_spec=BasicModelSpec,
    did=0,
    css=".card {\n font-family: arial;\n font-size: 20px;\n text-align: center;\n color: black;\n background-color: white;\n}\n",
)

BASIC_AND_REVERSED_CARD_MODEL = model.Model(
    name="Basic (and reversed card) (genanki)",
    model_spec=BasicModelSpec,
    css=".card {\n font-family: arial;\n font-size: 20px;\n text-align: center;\n color: black;\n background-color: white;\n}\n",
)

class OptionalReversedSpec(model.ModelSpec[Any]):
    @model.spec
    class fields(model.FieldSpec):
        Front: str = model.field()
        Back: str = model.field()
        Add_Reverse: str = model.field()

    @model.spec
    class templates(model.TemplateSpec[fields], fields=fields):
        card_1: str = model.template({
            "qfmt": "{{Front}}",
            "afmt": "{{FrontSide}}\n\n<hr id=answer>\n\n{{Back}}",
        })
        card_2: str = model.template({
            "qfmt": "{{#Add Reverse}}{{Back}}{{/Add Reverse}}",
            "afmt": "{{FrontSide}}\n\n<hr id=answer>\n\n{{Front}}",
        })


BASIC_OPTIONAL_REVERSED_CARD_MODEL = model.Model(
    name="Basic (optional reversed card) (genanki)",
    model_spec=OptionalReversedSpec,
    css=".card {\n font-family: arial;\n font-size: 20px;\n text-align: center;\n color: black;\n background-color: white;\n}\n",
)


class TypeInTheAnswerSpec(model.ModelSpec[Any]):
    @model.spec
    class fields(model.FieldSpec):
        Front: str = model.field()
        Back: str = model.field()

    @model.spec
    class templates(model.TemplateSpec[fields], fields=fields):
        card_1: str = model.template({
            "qfmt": "{{Front}}\n\n{{type:Back}}",
            "afmt": "{{FrontSide}}\n\n<hr id=answer>\n\n{{type:Back}}",
        })


BASIC_TYPE_IN_THE_ANSWER_MODEL = model.Model(
    name="Basic (type in the answer) (genanki)",
    model_spec=TypeInTheAnswerSpec,
    css=".card {\n font-family: arial;\n font-size: 20px;\n text-align: center;\n color: black;\n background-color: white;\n}\n",
)


class ClozeSpec(model.ModelSpec[Any]):
    @model.spec
    class fields(model.FieldSpec):
        Text: str = model.field()
        Back_Extra: str = model.field()

    @model.spec
    class templates(model.TemplateSpec[fields], fields=fields):
        cloze: str = model.template({
            "qfmt": "{{cloze:Text}}",
            "afmt": "{{cloze:Text}}<br>\n{{Back Extra}}",
        })


CLOZE_MODEL = model.Model(
    name="Cloze (genanki)",
    model_type=model.ModelType.CLOZE,
    model_spec=ClozeSpec,
    css=(
        ".card {\n font-family: arial;\n font-size: 20px;\n text-align: center;\n color: black;\n background-color: white;\n}\n\n"
        ".cloze {\n font-weight: bold;\n color: blue;\n}\n.nightMode .cloze {\n color: lightblue;\n}"
    ),
)


def _fix_deprecated_builtin_models_and_warn(model: model.Model[Any], fields: list[str]):
    if model is CLOZE_MODEL and len(fields) == 1:
        fixed_fields = [*fields, ""]
        warnings.warn(  # noqa: B028
            (
                "Using CLOZE_MODEL with a single field is deprecated."
                f" Please pass two fields, e.g. {fixed_fields!r} ."
                " See https://github.com/kerrickstaley/genanki#cloze_model-deprecationwarning ."
            ),
            DeprecationWarning,
        )
        return fixed_fields

    return fields
