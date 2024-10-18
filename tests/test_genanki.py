from collections.abc import Callable, Generator
import os
import sys

from _pytest.fixtures import SubRequest
from anki.media_pb2 import CheckMediaResponse
import genanki
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
import anki.importing.apkg

TEST_MODEL = genanki.model.Model(
    234567,
    "foomodel",
    fields=[
        {
            "name": "AField",
        },
        {
            "name": "BField",
        },
    ],
    templates=[
        {
            "name": "card1",
            "qfmt": "{{AField}}",
            "afmt": "{{FrontSide}}" '<hr id="answer">' "{{BField}}",
        }
    ],
)

TEST_CN_MODEL = genanki.model.Model(
    345678,
    "Chinese",
    fields=[{"name": "Traditional"}, {"name": "Simplified"}, {"name": "English"}],
    templates=[
        {
            "name": "Traditional",
            "qfmt": "{{Traditional}}",
            "afmt": "{{FrontSide}}" '<hr id="answer">' "{{English}}",
        },
        {
            "name": "Simplified",
            "qfmt": "{{Simplified}}",
            "afmt": "{{FrontSide}}" '<hr id="answer">' "{{English}}",
        },
    ],
)

TEST_MODEL_WITH_HINT = genanki.model.Model(
    456789,
    "with hint",
    fields=[{"name": "Question"}, {"name": "Hint"}, {"name": "Answer"}],
    templates=[
        {
            "name": "card1",
            "qfmt": "{{Question}}" "{{#Hint}}<br>Hint: {{Hint}}{{/Hint}}",
            "afmt": "{{Answer}}",
        },
    ],
)

# Same as default latex_pre but we include amsfonts package
CUSTOM_LATEX_PRE = (
    "\\documentclass[12pt]{article}\n\\special{papersize=3in,5in}\n\\usepackage[utf8]{inputenc}\n"
    "\\usepackage{amssymb,amsmath,amsfonts}\n\\pagestyle{empty}\n\\setlength{\\parindent}{0in}\n"
    "\\begin{document}\n"
)
# Same as default latex_post but we add a comment. (What is a real-world use-case for customizing latex_post?)
CUSTOM_LATEX_POST = "% here is a great comment\n\\end{document}"

TEST_MODEL_WITH_LATEX = genanki.model.Model(
    567890,
    "with latex",
    fields=[
        {
            "name": "AField",
        },
        {
            "name": "BField",
        },
    ],
    templates=[
        {
            "name": "card1",
            "qfmt": "{{AField}}",
            "afmt": "{{FrontSide}}" '<hr id="answer">' "{{BField}}",
        }
    ],
    latex_pre=CUSTOM_LATEX_PRE,
    latex_post=CUSTOM_LATEX_POST,
)

CUSTOM_SORT_FIELD_INDEX = 1  # Anki default value is 0
TEST_MODEL_WITH_SORT_FIELD_INDEX = genanki.model.Model(
    987123,
    "with sort field index",
    fields=[
        {
            "name": "AField",
        },
        {
            "name": "BField",
        },
    ],
    templates=[
        {
            "name": "card1",
            "qfmt": "{{AField}}",
            "afmt": "{{FrontSide}}" '<hr id="answer">' "{{BField}}",
        }
    ],
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


type AnkiCollectionFixture = anki.collection.Collection


@pytest.fixture(autouse=True, scope="function")
def anki_collection(request: SubRequest) -> Generator[AnkiCollectionFixture]:
    # TODO make this less messy
    with tempfile.NamedTemporaryFile(
        suffix=".anki2", delete=False, delete_on_close=False
    ) as colf:
        colf.close()  # colf is deleted
        yield anki.collection.Collection(colf.name)
        if not request.session.testsfailed:
            os.unlink(colf.name)


type ImportPackageFixture = Callable[[genanki.Package, float | None], None]


@pytest.fixture(autouse=False, scope="function")
def import_package(
    anki_collection: AnkiCollectionFixture,
) -> Generator[ImportPackageFixture]:
    with tempfile.NamedTemporaryFile(
        suffix=".apkg", delete=False, delete_on_close=False
    ) as outf:

        def import_package_fn(
            pkg: genanki.Package, timestamp: float | None = None
        ):
            """
            Imports `pkg` into self.col.

            :param genanki.Package pkg:
            """
            outf.close()

            pkg.write_to_file(outf.name, timestamp=timestamp)

            importer = anki.importing.apkg.AnkiPackageImporter(
                anki_collection, outf.name
            )
            importer.run()

        yield import_package_fn


type CheckMediaFixture = Callable[[], CheckMediaResponse]


@pytest.fixture(autouse=False, scope="function")
def check_media(
    anki_collection: AnkiCollectionFixture,
) -> Generator[CheckMediaFixture]:
    def check_media_fn():
        # col.media.check seems to assume that the cwd is the media directory. So this helper function
        # chdirs to the media dir before running check and then goes back to the original cwd.
        orig_cwd = os.getcwd()
        os.chdir(anki_collection.media.dir())
        ret = anki_collection.media.check()
        os.chdir(orig_cwd)
        return ret

    yield check_media_fn


def test_generated_deck_can_be_imported(
    anki_collection: AnkiCollectionFixture,
    import_package: ImportPackageFixture,
):
    deck = genanki.Deck(anki.decks.DeckId(123456), "foodeck")
    note = genanki.Note(TEST_MODEL, ["a", "b"])
    deck.add_note(note)

    import_package(genanki.Package(deck), None)

    all_imported_decks = anki_collection.decks.all()
    assert len(all_imported_decks) == 2  # default deck and foodeck
    assert any(anki_decks["name"] == "foodeck" for anki_decks in all_imported_decks)


def test_generated_deck_has_valid_cards(
    anki_collection: AnkiCollectionFixture, import_package: ImportPackageFixture
):
    """
    Generates a deck with several notes and verifies that the nid/ord combinations on the generated cards make sense.

    Catches a bug that was fixed in 08d8a139.
    """
    deck = genanki.Deck(anki.decks.DeckId(123456), "foodeck")
    deck.add_note(genanki.Note(TEST_CN_MODEL, ["a", "b", "c"]))  # 2 cards
    deck.add_note(genanki.Note(TEST_CN_MODEL, ["d", "e", "f"]))  # 2 cards
    deck.add_note(genanki.Note(TEST_CN_MODEL, ["g", "h", "i"]))  # 2 cards

    import_package(genanki.Package(deck), None)

    cards: list[anki.cards.Card] = [
        anki_collection.get_card(i) for i in anki_collection.find_cards("")
    ]

    # the bug causes us to fail to generate certain cards (e.g. the second card for the second note)
    assert len(cards) == 6


def test_multi_deck_package(
    anki_collection: AnkiCollectionFixture, import_package: ImportPackageFixture
):
    deck1 = genanki.Deck(anki.decks.DeckId(123456), "foodeck")
    deck2 = genanki.Deck(anki.decks.DeckId(654321), "bardeck")

    note = genanki.Note(TEST_MODEL, ["a", "b"])

    deck1.add_note(note)
    deck2.add_note(note)

    import_package(genanki.Package([deck1, deck2]), None)

    all_imported_decks = anki_collection.decks.all()
    assert len(all_imported_decks) == 3  # default deck, foodeck, and bardeck


def test_card_isEmpty__with_2_fields__succeeds(
    anki_collection: AnkiCollectionFixture, import_package: ImportPackageFixture
):
    """Tests for a bug in an early version of genanki where notes with <4 fields were not supported."""
    deck = genanki.Deck(anki.decks.DeckId(123456), "foodeck")
    note = genanki.Note(TEST_MODEL, ["a", "b"])
    deck.add_note(note)

    import_package(genanki.Package(deck), None)

    anki_note: anki.notes.Note = anki_collection.get_note(
        anki_collection.find_notes("")[0]
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
    n1 = genanki.Note(model=TEST_CN_MODEL, fields=["中國", "中国", "China"])
    # no 'Simplified' field, so it won't generate a 'Simplified' card
    n2 = genanki.Note(model=TEST_CN_MODEL, fields=["你好", "", "hello"])

    assert len(n1.cards) == 2
    assert n1.cards[0].ord == 0
    assert n1.cards[1].ord == 1

    assert len(n2.cards) == 1
    assert n2.cards[0].ord == 0


def test_notes_generate_cards_based_on_req__with_hint():
    # both of these notes will generate one card
    n1 = genanki.Note(
        model=TEST_MODEL_WITH_HINT,
        fields=["capital of California", "", "Sacramento"],
    )
    n2 = genanki.Note(
        model=TEST_MODEL_WITH_HINT,
        fields=["capital of Iowa", 'French for "The Moines"', "Des Moines"],
    )

    assert len(n1.cards) == 1
    assert n1.cards[0].ord == 0
    assert len(n2.cards) == 1
    assert n2.cards[0].ord == 0


def test_Note_with_guid_property():
    class MyNote(genanki.Note):
        @property
        def guid(self):
            return "3"

        @guid.setter
        def guid(self, val: str) -> None:
            raise NotImplementedError

    # test passes if this doesn't raise an exception
    MyNote()


def test_media_files(
    anki_collection: AnkiCollectionFixture,
    import_package: ImportPackageFixture,
    check_media: CheckMediaFixture,
):
    # change to a scratch directory so we can write files
    os.chdir(tempfile.mkdtemp())

    deck = genanki.Deck(anki.decks.DeckId(123456), "foodeck")
    note = genanki.Note(
        TEST_MODEL,
        [
            "question [sound:present.mp3] [sound:missing.mp3]",
            'answer <img src="present.jpg"> <img src="missing.jpg">',
        ],
    )
    deck.add_note(note)

    # populate files with data
    with open("present.mp3", "wb") as h:
        h.write(VALID_MP3)
    with open("present.jpg", "wb") as h:
        h.write(VALID_JPG)

    package = genanki.Package(deck, media_files=["present.mp3", "present.jpg"])
    import_package(package, None)

    os.remove("present.mp3")
    os.remove("present.jpg")

    res = check_media()
    assert set(res.missing) == {"missing.mp3", "missing.jpg"}


def test_media_files_in_subdirs(
    import_package: ImportPackageFixture, check_media: CheckMediaFixture
):
    # change to a scratch directory so we can write files
    os.chdir(tempfile.mkdtemp())

    deck = genanki.Deck(anki.decks.DeckId(123456), "foodeck")
    note = genanki.Note(
        TEST_MODEL,
        [
            "question [sound:present.mp3] [sound:missing.mp3]",
            'answer <img src="present.jpg"> <img src="missing.jpg">',
        ],
    )
    deck.add_note(note)

    # populate files with data
    os.mkdir("subdir1")
    with open("subdir1/present.mp3", "wb") as h:
        h.write(VALID_MP3)
    os.mkdir("subdir2")
    with open("subdir2/present.jpg", "wb") as h:
        h.write(VALID_JPG)

    package = genanki.Package(
        deck, media_files=["subdir1/present.mp3", "subdir2/present.jpg"]
    )
    import_package(package, None)

    os.remove("subdir1/present.mp3")
    os.remove("subdir2/present.jpg")

    res = check_media()
    assert set(res.missing) == {"missing.mp3", "missing.jpg"}


def test_media_files_absolute_paths(
    import_package: ImportPackageFixture, check_media: CheckMediaFixture
):
    # change to a scratch directory so we can write files
    os.chdir(tempfile.mkdtemp())
    media_dir = tempfile.mkdtemp()

    deck = genanki.Deck(anki.decks.DeckId(123456), "foodeck")
    note = genanki.Note(
        TEST_MODEL,
        [
            "question [sound:present.mp3] [sound:missing.mp3]",
            'answer <img src="present.jpg"> <img src="missing.jpg">',
        ],
    )
    deck.add_note(note)

    # populate files with data
    present_mp3_path = os.path.join(media_dir, "present.mp3")
    present_jpg_path = os.path.join(media_dir, "present.jpg")
    with open(present_mp3_path, "wb") as h:
        h.write(VALID_MP3)
    with open(present_jpg_path, "wb") as h:
        h.write(VALID_JPG)

    package = genanki.Package(deck, media_files=[present_mp3_path, present_jpg_path])
    import_package(package, None)

    res = check_media()
    assert set(res.missing) == {"missing.mp3", "missing.jpg"}


def test_write_deck_without_deck_id_fails(anki_collection: AnkiCollectionFixture):
    # change to a scratch directory so we can write files
    os.chdir(tempfile.mkdtemp())

    deck = genanki.Deck()
    deck.name = "foodeck"

    pkg = genanki.Package(deck)
    with pytest.raises(TypeError):
        pkg.write_to_file("foodeck.apkg")


def test_write_deck_without_name_fails(anki_collection: AnkiCollectionFixture):
    # change to a scratch directory so we can write files
    os.chdir(tempfile.mkdtemp())

    deck = genanki.Deck()
    deck.deck_id = anki.decks.DeckId(123456)

    pkg = genanki.Package(deck)

    with pytest.raises(TypeError):
        pkg.write_to_file("foodeck.apkg")


def test_card_suspend(
    anki_collection: AnkiCollectionFixture, import_package: ImportPackageFixture
):
    deck = genanki.Deck(anki.decks.DeckId(123456), "foodeck")
    note = genanki.Note(model=TEST_CN_MODEL, fields=["中國", "中国", "China"], guid="foo")
    assert len(note.cards) == 2

    note.cards[1].suspend = True

    deck.add_note(note)

    pkg = genanki.Package(deck, id_gen=iter([1, 2, 3, 4, 5]))

    import_package(pkg, None)

    assert anki_collection.find_cards("") == [2, 3]
    assert anki_collection.find_cards("is:suspended") == [3]


def test_deck_with_description(
    anki_collection: AnkiCollectionFixture, import_package: ImportPackageFixture
):
    deck = genanki.Deck(
        anki.decks.DeckId(112233),
        "foodeck",
        description="This is my great deck.\nIt is so so great.",
    )
    note = genanki.Note(TEST_MODEL, ["a", "b"])
    deck.add_note(note)

    import_package(genanki.Package(deck), None)

    all_decks = anki_collection.decks.all()
    assert len(all_decks) == 2  # default deck and foodeck
    assert any(anki_decks["name"] == "foodeck" for anki_decks in all_decks)


def test_card_added_date_is_recent(
    anki_collection: AnkiCollectionFixture, import_package: ImportPackageFixture
):
    """
    Checks for a bug where cards were assigned the creation date 1970-01-01 (i.e. the Unix epoch).

    See https://github.com/kerrickstaley/genanki/issues/29 .

    The "Added" date is encoded in the card.id field; see
    https://github.com/ankitects/anki/blob/ed8340a4e3a2006d6285d7adf9b136c735ba2085/anki/stats.py#L28

    TODO implement a fix so that this test passes.
    """
    deck = genanki.Deck(anki.decks.DeckId(1104693946), "foodeck")
    note = genanki.Note(TEST_MODEL, ["a", "b"])
    deck.add_note(note)

    import_package(genanki.Package(deck), None)

    anki_note = anki_collection.get_note(anki_collection.find_notes("")[0])
    anki_card = anki_note.cards()[0]

    assert anki_card.id > 1577836800000  # Jan 1 2020 UTC (milliseconds since epoch)


def test_model_with_latex_pre_and_post(
    anki_collection: AnkiCollectionFixture, import_package: ImportPackageFixture
):
    deck = genanki.Deck(anki.decks.DeckId(1681249286), "foodeck")
    note = genanki.Note(TEST_MODEL_WITH_LATEX, ["a", "b"])
    deck.add_note(note)

    import_package(genanki.Package(deck), None)

    anki_note = anki_collection.get_note(anki_collection.find_notes("")[0])
    t = anki_note.note_type()
    assert t is not None
    assert t["latexPre"] == CUSTOM_LATEX_PRE
    assert t["latexPost"] == CUSTOM_LATEX_POST


def test_model_with_sort_field_index(
    anki_collection: AnkiCollectionFixture, import_package: ImportPackageFixture
):
    deck = genanki.Deck(anki.decks.DeckId(332211), "foodeck")
    note = genanki.Note(TEST_MODEL_WITH_SORT_FIELD_INDEX, ["a", "3.A"])
    deck.add_note(note)

    import_package(genanki.Package(deck), None)

    anki_note = anki_collection.get_note(anki_collection.find_notes("")[0])
    t = anki_note.note_type()
    assert t is not None
    assert t["sortf"] == CUSTOM_SORT_FIELD_INDEX


def test_notes_with_due1(
    anki_collection: AnkiCollectionFixture, import_package: ImportPackageFixture
):
    deck = genanki.Deck(anki.decks.DeckId(4145273926), "foodeck")
    deck.add_note(genanki.Note(TEST_MODEL, ["Capital of Washington", "Olympia"], due=1))
    deck.add_note(genanki.Note(TEST_MODEL, ["Capital of Oregon", "Salem"], due=2))

    import_package(genanki.Package(deck), None)
    d = anki_collection.decks.id("foodeck")
    assert d is not None
    anki_collection.decks.select(d)
    anki_collection.sched.reset()
    next_card = anki_collection.sched.getCard()
    assert next_card is not None
    next_note = anki_collection.get_note(next_card.nid)

    # Next card is the one with lowest due value.
    assert next_note.fields == ["Capital of Washington", "Olympia"]


def test_notes_with_due2(
    anki_collection: AnkiCollectionFixture, import_package: ImportPackageFixture
):
    # Same as test_notes_with_due1, but we switch the due values
    # for the two notes.
    deck = genanki.Deck(anki.decks.DeckId(4145273927), "foodeck")
    deck.add_note(genanki.Note(TEST_MODEL, ["Capital of Washington", "Olympia"], due=2))
    deck.add_note(genanki.Note(TEST_MODEL, ["Capital of Oregon", "Salem"], due=1))

    import_package(genanki.Package(deck), None)

    d = anki_collection.decks.id("foodeck")
    assert d is not None
    anki_collection.decks.select(d)
    anki_collection.sched.reset()
    next_card = anki_collection.sched.getCard()
    assert next_card is not None
    next_note = anki_collection.get_note(next_card.nid)

    # Next card changes to "Capital of Oregon", because it has lower
    # due value.
    assert next_note.fields == ["Capital of Oregon", "Salem"]
