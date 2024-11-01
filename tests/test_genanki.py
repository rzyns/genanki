from contextlib import contextmanager
from functools import reduce
import os
import sys
from typing import Any, cast

import genanki
from genanki import collection
import genanki.deck
import genanki.model

sys.path.append(os.path.join(os.getcwd(), "anki_upstream"))

import pytest
import tempfile

import anki
import anki.collection
import anki.cards
import anki.decks
import anki.notes
import anki.models
import anki.importing
import anki.importing.apkg
from anki.media_pb2 import CheckMediaResponse

class ModelSpec1(genanki.model.ModelSpec[Any]):
    @genanki.model.spec
    class fields(genanki.model.FieldSpec):
        AField: str = genanki.model.field()
        BField: str = genanki.model.field()

    @genanki.model.spec
    class templates(genanki.model.TemplateSpec[fields], fields=fields):
        card1: str = genanki.model.template({
            "qfmt": "{{AField}}",
            "afmt": "{{FrontSide}}<hr id=answer>{{BField}}",
        })


TEST_MODEL = genanki.model.Model(
    # model_id=anki.models.NotetypeId(234567),
    name="foomodel",
    model_spec=ModelSpec1,
)


class CNModelSpec(genanki.model.ModelSpec[Any]):
    @genanki.model.spec
    class fields(genanki.model.FieldSpec):
        Traditional: str = genanki.model.field()
        Simplified: str = genanki.model.field()
        English: str = genanki.model.field()

    @genanki.model.spec
    class templates(genanki.model.TemplateSpec[fields], fields=fields):
        Traditional: str = genanki.model.template({
            "qfmt": "{{Traditional}}",
            "afmt": "{{FrontSide}}<hr id=answer>{{English}}",
        })
        Simplified: str = genanki.model.template({
            "qfmt": "{{Simplified}}",
            "afmt": "{{FrontSide}}<hr id=answer>{{English}}",
        })


TEST_CN_MODEL = genanki.model.Model(
    # model_id=anki.models.NotetypeId(345678),
    name="Chinese",
    model_spec=CNModelSpec,
)


class ModelWithHintSpec(genanki.model.ModelSpec[Any]):
    @genanki.model.spec
    class fields(genanki.model.FieldSpec):
        Question: str = genanki.model.field()
        Hint: str = genanki.model.field()
        Answer: str = genanki.model.field()

    @genanki.model.spec
    class templates(genanki.model.TemplateSpec[fields], fields=fields):
        card1: str = genanki.model.template({
            "qfmt": "{{Question}}{{#Hint}}<br>Hint: {{Hint}}{{/Hint}}",
            "afmt": "{{Answer}}",
        })


TEST_MODEL_WITH_HINT = genanki.model.Model(
    # model_id=anki.models.NotetypeId(456789),
    name="with hint",
    model_spec=ModelWithHintSpec,
)

# Same as default latex_pre but we include amsfonts package
CUSTOM_LATEX_PRE = (
    "\\documentclass[12pt]{article}\n\\special{papersize=3in,5in}\n\\usepackage[utf8]{inputenc}\n"
    "\\usepackage{amssymb,amsmath,amsfonts}\n\\pagestyle{empty}\n\\setlength{\\parindent}{0in}\n"
    "\\begin{document}\n"
)
# Same as default latex_post but we add a comment. (What is a real-world use-case for customizing latex_post?)
CUSTOM_LATEX_POST = "% here is a great comment\n\\end{document}"


class ModelWithLatexSpec(genanki.model.ModelSpec[Any]):
    @genanki.model.spec
    class fields(genanki.model.FieldSpec):
        AField: str = genanki.model.field()
        BField: str = genanki.model.field()

    @genanki.model.spec
    class templates(genanki.model.TemplateSpec[fields], fields=fields):
        card1: str = genanki.model.template({
            "qfmt": "{{AField}}",
            "afmt": "{{FrontSide}}<hr id=answer>{{BField}}",
        })


TEST_MODEL_WITH_LATEX = genanki.model.Model(
    # model_id=anki.models.NotetypeId(567890),
    name="with latex",
    model_spec=ModelWithLatexSpec,
    latex_pre=CUSTOM_LATEX_PRE,
    latex_post=CUSTOM_LATEX_POST,
)


class ModelWithSortFieldIndexSpec(genanki.model.ModelSpec[Any]):
    @genanki.model.spec
    class fields(genanki.model.FieldSpec):
        AField: str = genanki.model.field()
        BField: str = genanki.model.field()

    @genanki.model.spec
    class templates(genanki.model.TemplateSpec[fields], fields=fields):
        card1: str = genanki.model.template({
            "qfmt": "{{AField}}",
            "afmt": "{{FrontSide}}<hr id=answer>{{BField}}",
        })


CUSTOM_SORT_FIELD_INDEX = 1  # Anki default value is 0
TEST_MODEL_WITH_SORT_FIELD_INDEX = genanki.model.Model(
    # model_id=anki.models.NotetypeId(987123),
    name="with sort field index",
    model_spec=ModelWithSortFieldIndexSpec,
    sort_field_index=CUSTOM_SORT_FIELD_INDEX,
)

# VALID_MP3 and VALID_JPG courtesy of https://github.com/mathiasbynens/small
VALID_MP3 = (
    b"\xff\xe3\x18\xc4\x00\x00\x00\x03H\x00\x00\x00\x00LAME3.98.2\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)

VALID_JPG = (
    b"\xff\xd8\xff\xdb\x00C\x00\x03\x02\x02\x02\x02\x02\x03\x02\x02\x02\x03\x03"
    b"\x03\x03\x04\x06\x04\x04\x04\x04\x04\x08\x06\x06\x05\x06\t\x08\n\n\t\x08\t"
    b"\t\n\x0c\x0f\x0c\n\x0b\x0e\x0b\t\t\r\x11\r\x0e\x0f\x10\x10\x11\x10\n\x0c"
    b"\x12\x13\x12\x10\x13\x0f\x10\x10\x10\xff\xc9\x00\x0b\x08\x00\x01\x00\x01"
    b"\x01\x01\x11\x00\xff\xcc\x00\x06\x00\x10\x10\x05\xff\xda\x00\x08\x01\x01"
    b"\x00\x00?\x00\xd2\xcf \xff\xd9"
)


@contextmanager
def new_anki_collection():
    with collection.empty_collection(suffix=".anki2", delete=True) as colf:
        col = anki.collection.Collection(colf)
        col.reset()
        yield col


def import_package(col: anki.collection.Collection, file: str):
    # https://forums.ankiweb.net/t/working-with-an-ankideck-using-python/37311/3
    col.import_anki_package(
        anki.collection.ImportAnkiPackageRequest(
            package_path=file,
            options=anki.collection.ImportAnkiPackageOptions(
                with_deck_configs=True,
                with_scheduling=True,
            )
        )
    )


def check_media(anki_collection: anki.collection.Collection) -> CheckMediaResponse:
    # col.media.check seems to assume that the cwd is the media directory. So this helper function
    # chdirs to the media dir before running check and then goes back to the original cwd.
    orig_cwd = os.getcwd()
    os.chdir(anki_collection.media.dir())
    ret = anki_collection.media.check()
    os.chdir(orig_cwd)
    return ret


def test_generated_deck_can_be_imported():
    deck = genanki.Deck(deck_id=anki.decks.DeckId(123456), name="foodeck")
    note = genanki.Note(model=TEST_MODEL, fields=TEST_MODEL.model_spec.fields(AField="a", BField="b"))
    deck.add_note(note)

    with tempfile.NamedTemporaryFile(delete=True, delete_on_close=False, suffix=".apkg") as tmpfile:
        pkg = genanki.Package(deck)
        pkg.write_to_file(tmpfile.name)

        with new_anki_collection() as col:

            check_media(col)
            import_package(col, tmpfile.name)

            all_imported_decks = col.decks.all()
            assert len(all_imported_decks) == 2
            assert any(anki_deck["name"] == "foodeck" for anki_deck in all_imported_decks)


def test_generated_deck_has_valid_cards():
    """
    Generates a deck with several notes and verifies that the nid/ord combinations on the generated cards make sense.

    Catches a bug that was fixed in 08d8a139.
    """
    with collection.empty_collection(suffix=".anki2", delete=True) as colf:
        col = anki.collection.Collection(colf)
        deck = genanki.Deck(deck_id=anki.decks.DeckId(223457), name="foodeck")

        for note in [
            genanki.Note(model=TEST_CN_MODEL, fields=TEST_CN_MODEL.model_spec.fields(Traditional="a", Simplified="b", English="c")),
            genanki.Note(model=TEST_CN_MODEL, fields=TEST_CN_MODEL.model_spec.fields(Traditional="d", Simplified="e", English="f")),
            genanki.Note(model=TEST_CN_MODEL, fields=TEST_CN_MODEL.model_spec.fields(Traditional="g", Simplified="h", English="i")),
        ]:
            assert len(note.cards) == 2
            deck.add_note(note)

        with tempfile.NamedTemporaryFile(delete=True, delete_on_close=False, suffix=".apkg") as tmpfile:
            pkg = genanki.Package(deck)
            num_cards = reduce(lambda acc, note: acc + len(note.cards), deck.notes, 0)
            assert num_cards == 6

            pkg.write_to_file(tmpfile.name)

            import_package(col, tmpfile.name)

            cards: list[anki.cards.Card] = [
                col.get_card(i) for i in col.find_cards("")
            ]

            # the bug causes us to fail to generate certain cards (e.g. the second card for the second note)
            assert len(cards) == 6


def test_export():
    deck1 = genanki.Deck(deck_id=anki.decks.DeckId(123456), name="foodeck")

    note = genanki.Note(
        model=TEST_MODEL,
        fields=TEST_MODEL.model_spec.fields(
            AField="a",
            BField="b",
        ),
    )

    deck1.add_note(note)

    with tempfile.NamedTemporaryFile(delete=True, suffix=".apkg") as tmpfile:
        pkg = genanki.Package([deck1])
        pkg.write_to_file(tmpfile.name)

        with new_anki_collection() as col:
            import_package(col, tmpfile.name)


def test_multi_deck_package():
    deck1 = genanki.Deck(deck_id=anki.decks.DeckId(123456), name="foodeck")
    deck2 = genanki.Deck(deck_id=anki.decks.DeckId(654321), name="bardeck")

    note = genanki.Note(
        model=TEST_MODEL,
        fields=TEST_MODEL.model_spec.fields(
            AField="a",
            BField="b",
        ),
    )

    deck1.add_note(note)
    deck2.add_note(note)

    with tempfile.NamedTemporaryFile(delete=True, delete_on_close=False, suffix=".apkg") as tmpfile:
        pkg = genanki.Package([deck1, deck2])
        pkg.write_to_file(tmpfile.name)

        with new_anki_collection() as col:
            import_package(col, tmpfile.name)

        all_imported_decks = col.decks.all()
        assert len(all_imported_decks) == 3  # default deck, foodeck, and bardeck


def test_card_isEmpty__with_2_fields__succeeds():
    """Tests for a bug in an early version of genanki where notes with <4 fields were not supported."""
    deck = genanki.Deck(deck_id=anki.decks.DeckId(123456), name="foodeck")
    note = genanki.Note(model=TEST_MODEL, fields=TEST_MODEL.model_spec.fields(AField="a", BField="b"))
    deck.add_note(note)

    with tempfile.NamedTemporaryFile(delete=True, delete_on_close=False, suffix=".apkg") as tmpfile:
        pkg = genanki.Package(deck)
        pkg.write_to_file(tmpfile.name)

        with new_anki_collection() as col:
            import_package(col, tmpfile.name)

            anki_note: anki.notes.Note = col.get_note(
                col.find_notes("")[0]
            )
            anki_card: anki.cards.Card = anki_note.cards()[0]

            # test passes if this doesn't raise an exception
            anki_card.is_empty()


def test_Model_req():
    assert TEST_MODEL._req == [(0, "all", [0])]


def test_Model_req__cn():
    assert TEST_CN_MODEL._req == [(0, "all", [0]), (1, "all", [1])]


def test_Model_req__with_hint():
    assert TEST_MODEL_WITH_HINT._req == [(0, "any", [0, 1])]


def test_notes_generate_cards_based_on_req__cn():
    # has 'Simplified' field, will generate a 'Simplified' card
    n1 = genanki.Note(model=TEST_CN_MODEL, fields=TEST_CN_MODEL.model_spec.fields(Traditional="中國", Simplified="中国", English="China"))
    # no 'Simplified' field, so it won't generate a 'Simplified' card
    n2 = genanki.Note(model=TEST_CN_MODEL, fields=TEST_CN_MODEL.model_spec.fields(Traditional="你好", Simplified="", English="hello"))

    assert len(n1.cards) == 2
    assert n1.cards[0].ord == 0
    assert n1.cards[1].ord == 1

    assert len(n2.cards) == 1
    assert n2.cards[0].ord == 0


def test_notes_generate_cards_based_on_req__with_hint():
    # both of these notes will generate one card
    n1 = genanki.Note(
        model=TEST_MODEL_WITH_HINT,
        fields=TEST_MODEL_WITH_HINT.model_spec.fields(Question="capital of California", Hint="", Answer="Sacramento"),
    )
    n2 = genanki.Note(
        model=TEST_MODEL_WITH_HINT,
        fields=TEST_MODEL_WITH_HINT.model_spec.fields(Question="capital of Iowa", Hint='French for "The Moines"', Answer="Des Moines"),
    )

    assert len(n1.cards) == 1
    assert n1.cards[0].ord == 0
    assert len(n2.cards) == 1
    assert n2.cards[0].ord == 0


def test_Note_with_guid_property():
    class MyNote(genanki.Note[Any]):
        @property
        def guid(self):
            return "3"

        @guid.setter
        def guid(self, val: str) -> None:
            raise NotImplementedError

    # test passes if this doesn't raise an exception
    cast(Any, MyNote)()


def test_media_files():
    # change to a scratch directory so we can write files
    os.chdir(tempfile.mkdtemp())

    deck = genanki.Deck(deck_id=anki.decks.DeckId(123456), name="foodeck")
    note = genanki.Note(
        model=TEST_MODEL,
        fields=TEST_MODEL.model_spec.fields(
            AField="question [sound:present.mp3] [sound:missing.mp3]",
            BField='answer <img src="present.jpg"> <img src="missing.jpg">',
        ),
    )
    deck.add_note(note)

    # populate files with data
    with open("present.mp3", "wb") as h:
        h.write(VALID_MP3)
    with open("present.jpg", "wb") as h:
        h.write(VALID_JPG)

    with tempfile.NamedTemporaryFile(delete=True, delete_on_close=False, suffix=".apkg") as tmpfile:
        package = genanki.Package(deck, media_files=["present.mp3", "present.jpg"])
        package.write_to_file(tmpfile.name)

        with new_anki_collection() as col:
            import_package(col, tmpfile.name)

            os.remove("present.mp3")
            os.remove("present.jpg")

            res = check_media(col)
            assert set(res.missing) == {"missing.mp3", "missing.jpg"}


def test_media_files_in_subdirs():
    # change to a scratch directory so we can write files
    os.chdir(tempfile.mkdtemp())

    deck = genanki.Deck(deck_id=anki.decks.DeckId(123456), name="foodeck")
    note = genanki.Note(
        model=TEST_MODEL,
        fields=TEST_MODEL.model_spec.fields(
            AField="question [sound:present.mp3] [sound:missing.mp3]",
            BField='answer <img src="present.jpg"> <img src="missing.jpg">',
        ),
    )
    deck.add_note(note)

    # populate files with data
    os.mkdir("subdir1")
    with open("subdir1/present.mp3", "wb") as h:
        h.write(VALID_MP3)
    os.mkdir("subdir2")
    with open("subdir2/present.jpg", "wb") as h:
        h.write(VALID_JPG)

    with tempfile.NamedTemporaryFile(delete=True, delete_on_close=False, suffix=".apkg") as tmpfile:
        package = genanki.Package(deck, media_files=["subdir1/present.mp3", "subdir2/present.jpg"])
        package.write_to_file(tmpfile.name)

        with new_anki_collection() as col:
            import_package(col, tmpfile.name)

            os.remove("subdir1/present.mp3")
            os.remove("subdir2/present.jpg")

            res = check_media(col)
            assert set(res.missing) == {"missing.mp3", "missing.jpg"}


def test_media_files_absolute_paths():
    # change to a scratch directory so we can write files
    os.chdir(tempfile.mkdtemp())
    media_dir = tempfile.mkdtemp()

    deck = genanki.Deck(deck_id=anki.decks.DeckId(123456), name="foodeck")
    note = genanki.Note(
        model=TEST_MODEL,
        fields=TEST_MODEL.model_spec.fields(
            AField="question [sound:present.mp3] [sound:missing.mp3]",
            BField='answer <img src="present.jpg"> <img src="missing.jpg">',
        ),
    )
    deck.add_note(note)

    # populate files with data
    present_mp3_path = os.path.join(media_dir, "present.mp3")
    present_jpg_path = os.path.join(media_dir, "present.jpg")
    with open(present_mp3_path, "wb") as h:
        h.write(VALID_MP3)
    with open(present_jpg_path, "wb") as h:
        h.write(VALID_JPG)

    with tempfile.NamedTemporaryFile(delete=True, delete_on_close=False, suffix=".apkg") as tmpfile:
        package = genanki.Package(deck, media_files=[present_mp3_path, present_jpg_path])
        package.write_to_file(tmpfile.name)

        with new_anki_collection() as col:
            import_package(col, tmpfile.name)

            res = check_media(col)
            assert set(res.missing) == {"missing.mp3", "missing.jpg"}


def test_write_deck_without_deck_id_fails():
    # change to a scratch directory so we can write files
    os.chdir(tempfile.mkdtemp())

    deck = genanki.Deck(name="foodeck")

    pkg = genanki.Package(deck)
    with pytest.raises(TypeError):
        pkg.write_to_file("foodeck.apkg")


def test_write_deck_without_name_fails():
    # change to a scratch directory so we can write files
    os.chdir(tempfile.mkdtemp())

    deck = genanki.Deck(name="foodeck")
    deck.deck_id = anki.decks.DeckId(123456)

    pkg = genanki.Package(deck)

    with pytest.raises(TypeError):
        pkg.write_to_file("foodeck.apkg")


def test_card_suspend():
    deck = genanki.Deck(deck_id=anki.decks.DeckId(123456), name="foodeck")
    note = genanki.Note(model=TEST_CN_MODEL, fields=TEST_CN_MODEL.model_spec.fields(Traditional="中國", Simplified="中国", English="China"), guid="foo")
    assert len(note.cards) == 2

    note.cards[1].suspend = True

    deck.add_note(note)

    with tempfile.NamedTemporaryFile(delete=True, delete_on_close=False, suffix=".apkg") as tmpfile:
        pkg = genanki.Package(deck, id_gen=iter([1, 2, 3, 4, 5]))
        pkg.write_to_file(tmpfile.name)

        with new_anki_collection() as col:
            import_package(col, tmpfile.name)

            assert col.find_cards("") == [2, 3]
            assert col.find_cards("is:suspended") == [3]


def test_deck_with_description():
    deck = genanki.Deck(
        deck_id=anki.decks.DeckId(112233),
        name="foodeck",
        description="This is my great deck.\nIt is so so great.",
    )
    note = genanki.Note(model=TEST_MODEL, fields=TEST_MODEL.model_spec.fields(AField="a", BField="b"))
    deck.add_note(note)

    with tempfile.NamedTemporaryFile(delete=True, delete_on_close=False, suffix=".apkg") as tmpfile:
        pkg = genanki.Package(deck)
        pkg.write_to_file(tmpfile.name)

        with new_anki_collection() as col:
            import_package(col, tmpfile.name)

            all_decks = col.decks.all()
            assert len(all_decks) == 2  # default deck and foodeck
            assert any(anki_decks["name"] == "foodeck" for anki_decks in all_decks)


def test_card_added_date_is_recent():
    """
    Checks for a bug where cards were assigned the creation date 1970-01-01 (i.e. the Unix epoch).

    See https://github.com/kerrickstaley/genanki/issues/29 .

    The "Added" date is encoded in the card.id field; see
    https://github.com/ankitects/anki/blob/ed8340a4e3a2006d6285d7adf9b136c735ba2085/anki/stats.py#L28

    TODO implement a fix so that this test passes.
    """
    deck = genanki.Deck(deck_id=anki.decks.DeckId(1104693946), name="foodeck")
    note = genanki.Note(model=TEST_MODEL, fields=TEST_MODEL.model_spec.fields(AField="a", BField="b"))
    deck.add_note(note)

    with tempfile.NamedTemporaryFile(delete=True, delete_on_close=False, suffix=".apkg") as tmpfile:
        pkg = genanki.Package(deck)
        pkg.write_to_file(tmpfile.name)

        with new_anki_collection() as col:
            import_package(col, tmpfile.name)

            anki_note = col.get_note(col.find_notes("")[0])
            anki_card = anki_note.cards()[0]

            assert anki_card.id > 1577836800000  # Jan 1 2020 UTC (milliseconds since epoch)


def test_model_with_latex_pre_and_post():
    deck = genanki.Deck(deck_id=anki.decks.DeckId(1681249286), name="foodeck")
    note = genanki.Note(model=TEST_MODEL_WITH_LATEX, fields=TEST_MODEL_WITH_LATEX.model_spec.fields(AField="a", BField="b"))
    deck.add_note(note)

    with tempfile.NamedTemporaryFile(delete=True, delete_on_close=False, suffix=".apkg") as tmpfile:
        pkg = genanki.Package(deck)
        pkg.write_to_file(tmpfile.name)

        with new_anki_collection() as col:
            import_package(col, tmpfile.name)

            anki_note = col.get_note(col.find_notes("")[0])

            t = anki_note.note_type()
            assert t is not None
            assert t["latexPre"] == CUSTOM_LATEX_PRE
            assert t["latexPost"] == CUSTOM_LATEX_POST


def test_model_with_sort_field_index():
    deck = genanki.Deck(deck_id=anki.decks.DeckId(332211), name="foodeck")
    note = genanki.Note(model=TEST_MODEL_WITH_SORT_FIELD_INDEX, fields=TEST_MODEL_WITH_SORT_FIELD_INDEX.model_spec.fields(AField="a", BField="3.A"))
    deck.add_note(note)

    with tempfile.NamedTemporaryFile(delete=True, delete_on_close=False, suffix=".apkg") as tmpfile:
        pkg = genanki.Package(deck)
        pkg.write_to_file(tmpfile.name)

        with new_anki_collection() as col:
            import_package(col, tmpfile.name)

            anki_note = col.get_note(col.find_notes("")[0])
            t = anki_note.note_type()
            assert t is not None
            assert t["sortf"] == CUSTOM_SORT_FIELD_INDEX


def test_notes_with_due1():
    deck = genanki.Deck(deck_id=anki.decks.DeckId(4145273926), name="foodeck")
    deck.add_note(genanki.Note(model=TEST_MODEL, fields=TEST_MODEL.model_spec.fields(AField="Capital of Washington", BField="Olympia"), due=1))
    deck.add_note(genanki.Note(model=TEST_MODEL, fields=TEST_MODEL.model_spec.fields(AField="Capital of Oregon", BField="Salem"), due=2))

    with tempfile.NamedTemporaryFile(delete=True, delete_on_close=False, suffix=".apkg") as tmpfile:
        pkg = genanki.Package(deck)
        pkg.write_to_file(tmpfile.name)

        with new_anki_collection() as col:
            import_package(col, tmpfile.name)

            d = col.decks.id("foodeck")
            assert d is not None

            col.decks.select(d)
            col.sched.reset()

            next_card = col.sched.getCard()
            assert next_card is not None

            next_note = col.get_note(next_card.nid)

            # Next card is the one with lowest due value.
            assert next_note.fields == ["Capital of Washington", "Olympia"]


def test_notes_with_due2():
    # Same as test_notes_with_due1, but we switch the due values
    # for the two notes.
    deck = genanki.Deck(deck_id=anki.decks.DeckId(4145273927), name="foodeck")
    deck.add_note(genanki.Note(model=TEST_MODEL, fields=TEST_MODEL.model_spec.fields(AField="Capital of Washington", BField="Olympia"), due=2))
    deck.add_note(genanki.Note(model=TEST_MODEL, fields=TEST_MODEL.model_spec.fields(AField="Capital of Oregon", BField="Salem"), due=1))

    with tempfile.NamedTemporaryFile(delete=True, delete_on_close=False, suffix=".apkg") as tmpfile:
        pkg = genanki.Package(deck)
        pkg.write_to_file(tmpfile.name)

        with new_anki_collection() as col:
            import_package(col, tmpfile.name)

            d = col.decks.id("foodeck")
            assert d is not None
            col.decks.select(d)
            col.sched.reset()
            next_card = col.sched.getCard()
            assert next_card is not None
            next_note = col.get_note(next_card.nid)

            # Next card changes to "Capital of Oregon", because it has lower
            # due value.
            assert next_note.fields == ["Capital of Oregon", "Salem"]
