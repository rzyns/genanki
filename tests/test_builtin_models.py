import genanki
import os
import tempfile
import warnings

import anki.decks


DECK_ID = anki.decks.DeckId(1598559905)


def test_builtin_models():
    my_deck = genanki.Deck(deck_id=DECK_ID, name="Country Capitals")

    my_deck.add_note(
        genanki.Note[genanki.BASIC_MODEL.model_spec.fields](
            model=genanki.BASIC_MODEL, fields=genanki.BASIC_MODEL.model_spec.fields(Front="Capital of Argentina", Back="Buenos Aires")
        )
    )

    my_deck.add_note(
        genanki.Note[genanki.BASIC_AND_REVERSED_CARD_MODEL.model_spec.fields](
            model=genanki.BASIC_AND_REVERSED_CARD_MODEL,
            fields=genanki.BASIC_AND_REVERSED_CARD_MODEL.model_spec.fields(Front="Costa Rica", Back="San José"),
        )
    )

    my_deck.add_note(
        genanki.Note[genanki.BASIC_OPTIONAL_REVERSED_CARD_MODEL.model_spec.fields](
            model=genanki.BASIC_OPTIONAL_REVERSED_CARD_MODEL,
            fields=genanki.BASIC_OPTIONAL_REVERSED_CARD_MODEL.model_spec.fields(Front="France", Back="Paris", Add_Reverse="y"),
        )
    )

    my_deck.add_note(
        genanki.Note[genanki.BASIC_TYPE_IN_THE_ANSWER_MODEL.model_spec.fields](
            model=genanki.BASIC_TYPE_IN_THE_ANSWER_MODEL, fields=genanki.BASIC_TYPE_IN_THE_ANSWER_MODEL.model_spec.fields(Front="Taiwan", Back="Taipei")
        )
    )

    my_deck.add_note(
        genanki.Note[genanki.CLOZE_MODEL.model_spec.fields](
            model=genanki.CLOZE_MODEL,
            fields=genanki.CLOZE_MODEL.model_spec.fields(
                Text="{{c1::Ottawa}} is the capital of {{c2::Canada}}",
                Back_Extra="Ottawa is in Ontario province.",
            ),
        )
    )

    # Just try writing the notes to a .apkg file; if there is no Exception and no Warnings, we assume
    # things are good.
    fnode, fpath = tempfile.mkstemp()
    os.close(fnode)

    pkg = genanki.Package(my_deck)
    with warnings.catch_warnings(record=True) as warning_list:
        pkg.write_to_file(fpath)

    assert not warning_list

    os.unlink(fpath)
