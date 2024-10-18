import genanki
import os
import pytest
import tempfile
import warnings

import anki.decks


DECK_ID = anki.decks.DeckId(1598559905)


def test_builtin_models():
    my_deck = genanki.Deck(DECK_ID, "Country Capitals")

    my_deck.add_note(
        genanki.Note(
            model=genanki.BASIC_MODEL, fields=["Capital of Argentina", "Buenos Aires"]
        )
    )

    my_deck.add_note(
        genanki.Note(
            model=genanki.BASIC_AND_REVERSED_CARD_MODEL,
            fields=["Costa Rica", "San José"],
        )
    )

    my_deck.add_note(
        genanki.Note(
            model=genanki.BASIC_OPTIONAL_REVERSED_CARD_MODEL,
            fields=["France", "Paris", "y"],
        )
    )

    my_deck.add_note(
        genanki.Note(
            model=genanki.BASIC_TYPE_IN_THE_ANSWER_MODEL, fields=["Taiwan", "Taipei"]
        )
    )

    my_deck.add_note(
        genanki.Note(
            model=genanki.CLOZE_MODEL,
            fields=[
                "{{c1::Ottawa}} is the capital of {{c2::Canada}}",
                "Ottawa is in Ontario province.",
            ],
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


def test_cloze_with_single_field_warns():
    my_deck = genanki.Deck(DECK_ID, "Country Capitals")

    note = genanki.Note(
        model=genanki.CLOZE_MODEL,
        fields=["{{c1::Rome}} is the capital of {{c2::Italy}}"],
    )

    my_deck.add_note(note)

    fnode, fpath = tempfile.mkstemp()
    os.close(fnode)

    pkg = genanki.Package(my_deck)
    with pytest.warns(DeprecationWarning):
        pkg.write_to_file(fpath)

    os.unlink(fpath)
