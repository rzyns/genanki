"""Test creating Cloze cards"""
# https://apps.ankiweb.net/docs/manual20.html#cloze-deletion

import sys
from typing import Any
from genanki import Model
from genanki import Note
from genanki import Deck
from genanki import Package

import anki.decks
import anki.models
from genanki import model


CSS = """.card {
 font-family: arial;
 font-size: 20px;
 text-align: center;
 color: black;
 background-color: white;
}

.cloze {
 font-weight: bold;
 color: blue;
}
.nightMode .cloze {
 color: lightblue;
}
"""


class MyClozeModelSpec(model.ModelSpec[Any]):
    @model.spec
    class fields(model.FieldSpec):
        Text: str = model.field()
        Extra: str = model.field()


    @model.spec
    class templates(model.TemplateSpec[fields], fields=fields):
        my_cloze_card: str = model.template({
            "qfmt": "{{cloze:Text}}",
            "afmt": "{{cloze:Text}}<br>{{Extra}}",
        })


MY_CLOZE_MODEL = Model(
    # model_id=anki.models.NotetypeId(998877661),
    name="My Cloze Model",
    model_spec=MyClozeModelSpec,
    css=CSS,
    model_type=model.ModelType.CLOZE,
)


class MultiFieldClozeModelSpec(model.ModelSpec[Any]):
    @model.spec
    class fields(model.FieldSpec):
        Text1: str = model.field()
        Text2: str = model.field()


    @model.spec
    class templates(model.TemplateSpec[fields], fields=fields):
        cloze: str = model.template({
            "qfmt": "{{cloze:Text1}} and {{cloze:Text2}}",
            "afmt": "{{cloze:Text1}} and {{cloze:Text2}}",
        })


# This doesn't seem to be very useful but Anki supports it and so do we *shrug*
MULTI_FIELD_CLOZE_MODEL = model.Model(
    # model_id=anki.models.NotetypeId(1047194615),
    name="Multi Field Cloze Model",
    model_spec=MultiFieldClozeModelSpec,
    css=CSS,
    model_type=model.ModelType.CLOZE,
)


def test_cloze(write_to_test_apkg: bool = False):
    """Test Cloze model"""
    notes: list[Note[Any]] = []
    assert MY_CLOZE_MODEL.to_json(0, anki.decks.DeckId(0))["type"] == model.ModelType.CLOZE

    # Question: NOTE ONE: [...]
    # Answer:   NOTE ONE: single deletion
    my_cloze_note = Note(
        model=MY_CLOZE_MODEL,
        fields=MY_CLOZE_MODEL.model_spec.fields(
            Text="NOTE ONE: {{c1::single deletion}}",
            Extra=""
        ),
    )

    assert my_cloze_note.cards
    assert {card.ord for card in my_cloze_note.cards} == {0}
    notes.append(my_cloze_note)

    # Question: NOTE TWO: [...]              2nd deletion     3rd deletion
    # Answer:   NOTE TWO: **1st deletion**   2nd deletion     3rd deletion
    #
    # Question: NOTE TWO: 1st deletion       [...]            3rd deletion
    # Answer:   NOTE TWO: 1st deletion     **2nd deletion**   3rd deletion
    #
    # Question: NOTE TWO: 1st deletion       2nd deletion     [...]
    # Answer:   NOTE TWO: 1st deletion       2nd deletion   **3rd deletion**
    fields = [
        "NOTE TWO: {{c1::1st deletion}} {{c2::2nd deletion}} {{c3::3rd deletion}}",
        "",
    ]

    my_cloze_note = Note[MY_CLOZE_MODEL.model_spec.fields](
        model=MY_CLOZE_MODEL,
        fields=MY_CLOZE_MODEL.model_spec.fields(
            Text=fields[0],
            Extra=fields[1],
        ),
    )

    assert sorted(card.ord for card in my_cloze_note.cards) == [0, 1, 2]
    notes.append(my_cloze_note)

    # Question: NOTE THREE: C1-CLOZE
    # Answer:   NOTE THREE: 1st deletion
    fields = MY_CLOZE_MODEL.model_spec.fields(
        Text="NOTE THREE: {{c1::1st deletion::C1-CLOZE}}",
        Extra="",
    )

    my_cloze_note = Note[Any](model=MY_CLOZE_MODEL, fields=fields)
    assert {card.ord for card in my_cloze_note.cards} == {0}
    notes.append(my_cloze_note)

    # Question: NOTE FOUR: [...] foo 2nd deletion bar [...]
    # Answer:   NOTE FOUR: 1st deletion foo 2nd deletion bar 3rd deletion
    fields = MY_CLOZE_MODEL.model_spec.fields(
        Text="NOTE FOUR: {{c1::1st deletion}} foo {{c2::2nd deletion}} bar {{c1::3rd deletion}}",
        Extra="",
    )

    my_cloze_note = Note[Any](model=MY_CLOZE_MODEL, fields=fields)
    assert sorted(card.ord for card in my_cloze_note.cards) == [0, 1]
    notes.append(my_cloze_note)

    if write_to_test_apkg:
        _wr_apkg(notes)


def _wr_apkg(notes: list[Note[Any]]):
    """Write cloze cards to an Anki apkg file"""
    deckname = "mtherieau"
    deck = Deck(deck_id=anki.decks.DeckId(0), name=deckname)
    for note in notes:
        deck.add_note(note)
    fout_anki = f"{deckname}.apkg"
    Package(deck).write_to_file(fout_anki)
    print(f"  {len(notes)} Notes WROTE: {fout_anki}")


def test_cloze_multi_field():
    fields = MULTI_FIELD_CLOZE_MODEL.model_spec.fields(
        Text1="{{c1::Berlin}} is the capital of {{c2::Germany}}",
        Text2="{{c3::Paris}} is the capital of {{c4::France}}",
    )

    note = Note[MULTI_FIELD_CLOZE_MODEL.model_spec.fields](model=MULTI_FIELD_CLOZE_MODEL, fields=fields)
    assert sorted(card.ord for card in note.cards) == [0, 1, 2, 3]


def test_cloze_indicies_do_not_start_at_1():
    fields = MY_CLOZE_MODEL.model_spec.fields(
        Text="{{c2::Mitochondria}} are the {{c3::powerhouses}} of the cell",
        Extra="",
    )
    note = Note[MY_CLOZE_MODEL.model_spec.fields](model=MY_CLOZE_MODEL, fields=fields)
    assert sorted(card.ord for card in note.cards) == [1, 2]


def test_cloze_newlines_in_deletion():
    fields = MY_CLOZE_MODEL.model_spec.fields(
        Text="{{c1::Washington, D.C.}} is the capital of {{c2::the\nUnited States\nof America}}",
        Extra="",
    )
    note = Note[MY_CLOZE_MODEL.model_spec.fields](model=MY_CLOZE_MODEL, fields=fields)
    assert sorted(card.ord for card in note.cards) == [0, 1]


if __name__ == "__main__":
    test_cloze(len(sys.argv) != 1)
