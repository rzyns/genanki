from typing import Any
import anki.collection  # type: ignore
import anki.decks  # type: ignore # noqa F401

from anki.decks import DeckId
from genanki import model


class MSpec(model.ModelSpec[Any]):
    @model.spec
    class fields(model.FieldSpec):
        Front: str = model.field()
        Back: str = model.field()

    @model.spec
    class templates(model.TemplateSpec[fields], fields=fields):
        front_back: str = model.template({
            "qfmt": "{{Front}}",
            "afmt": "{{Front}} => {{Back}}",
        })


def test_dataclass_transform():
    spec1 = MSpec.fields(Front="Front", Back="Back")

    assert spec1.Front == "Front"
    assert spec1.__dataclass_fields__["Front"].__genanki_field__.items() >= ({"name": "Front"}).items()

    assert spec1.Back == "Back"
    assert spec1.__dataclass_fields__["Back"].__genanki_field__.items() >= ({"name": "Back"}).items()

def test_model():
    deck_id = DeckId(0)

    m = model.VirtualModel(
        name="A Model",
        model_spec=MSpec,
        did=deck_id,
    )

    data = m.to_json(deck_id=deck_id, timestamp=0)

    assert data["css"] == m.css
    assert data["did"] == 0
    assert data["flds"][0]["name"] == "Front"
    assert data["flds"][1]["name"] == "Back"
    # "id": m.id,
    assert data["latexPost"] == ""
    assert data["latexPre"] == ""
    assert data["mod"] == 0
    assert data["name"] == "A Model"

    assert data["req"] == [
        (0, "all", [0, 1]),
    ]
    assert data["sortf"] == 0
    assert data["tmpls"][0].items() >= ({
        "afmt": "{{Front}} => {{Back}}",
        "name": "front_back",
        "qfmt": "{{Front}}",
    }).items()
