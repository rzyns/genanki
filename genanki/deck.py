import itertools
import json
import os
import sqlite3
import tempfile
import time
import zipfile
from sqlite3 import Cursor
from typing import Protocol
from collections.abc import Iterable

import anki
import anki.collection
import anki.lang
import anki.decks

from .apkg_col import APKG_COL
from .apkg_schema import APKG_SCHEMA
# from .deck import Deck
from .model import Model
from .note import Note


if anki.lang.current_i18n is None:
    anki.lang.set_lang("en")


class SupportsNext[T](Protocol):
    def __next__(self) -> T: ...


class Package:
    decks: list["Deck"]
    id_gen: SupportsNext[int] | None

    def __init__(
        self,
        deck_or_decks: "Deck | Iterable[Deck] | None" = None,
        media_files: Iterable[str] | None = None,
        id_gen: SupportsNext[int] | None = None,
    ):
        if isinstance(deck_or_decks, Deck):
            self.decks = [deck_or_decks]
        elif deck_or_decks is None:
            self.decks = []
        else:
            self.decks = list(deck_or_decks)

        self.media_files = media_files or []
        self.id_gen = id_gen

    def write_to_file(self, file: str, timestamp: float | None = None, id_gen: SupportsNext[int] | None = None) -> None:
        """
        :param file: File path to write to.
        :param timestamp: Timestamp (float seconds since Unix epoch) to assign to generated notes/cards. Can be used to
            make build hermetic. Defaults to time.time().
        """
        dbfile, dbfilename = tempfile.mkstemp()
        os.close(dbfile)

        conn = sqlite3.connect(dbfilename)
        cursor = conn.cursor()

        if timestamp is None:
            timestamp = time.time()

        id_gen = id_gen or self.id_gen or itertools.count(int(timestamp * 1000))
        self.write_to_db(cursor, timestamp, id_gen)

        conn.commit()
        conn.close()

        with zipfile.ZipFile(file, "w") as outzip:
            outzip.write(dbfilename, "collection.anki2")

            media_file_idx_to_path = dict(enumerate(self.media_files))
            media_json = {
                idx: os.path.basename(path)
                for idx, path in media_file_idx_to_path.items()
            }
            outzip.writestr("media", json.dumps(media_json))

            for idx, path in media_file_idx_to_path.items():
                outzip.write(path, str(idx))

    def write_to_db[T](
        self, cursor: sqlite3.Cursor, timestamp: float, id_gen: SupportsNext[T]
    ) -> None:
        cursor.executescript(APKG_SCHEMA)
        cursor.executescript(APKG_COL)

        for deck in self.decks:
            deck.write_to_db(cursor, timestamp, id_gen)

    def write_to_collection_from_addon(self):
        """
        Write to local collection. *Only usable when running inside an Anki addon!* Only tested on Anki 2.1.

        This writes to a temporary file and then calls the code that Anki uses to import packages.

        Note: the caller may want to use mw.checkpoint and mw.reset as follows:

          # creates a menu item called "Undo Add Notes From MyAddon" after this runs
          mw.checkpoint('Add Notes From MyAddon')
          # run import
          my_package.write_to_collection_from_addon()
          # refreshes main view so new deck is visible
          mw.reset()

        Tip: if your deck has the same name and ID as an existing deck, then the notes will get placed in that deck rather
        than a new deck being created.
        """
        from anki.importing.apkg import AnkiPackageImporter  # noqa: PLC0415
        from aqt import mw  # main window  # noqa: PLC0415

        if mw is not None and mw.col is not None:
            with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
                self.write_to_file(tmpfile.name)
                AnkiPackageImporter(mw.col, tmpfile.name).run()


class Deck:
    notes: list[Note]
    models: dict[int, Model]

    def __init__(
        self,
        deck_id: anki.decks.DeckId | None = None,
        name: str | None = None,
        description: str = "",
    ):
        self.deck_id = deck_id
        self.name = name
        self.description = description
        self.notes = []
        self.models = {}  # map of model id to model

    def add_note(self, note: Note) -> None:
        self.notes.append(note)

    def add_model(self, model: Model):
        if model.model_id is None:
            raise ValueError("Model ID must not be None.")
        self.models[model.model_id] = model

    def to_json(self):
        return {
            "collapsed": False,
            "conf": 1,
            "desc": self.description,
            "dyn": 0,
            "extendNew": 0,
            "extendRev": 50,
            "id": self.deck_id,
            "lrnToday": [163, 2],
            "mod": 1425278051,
            "name": self.name,
            "newToday": [163, 2],
            "revToday": [163, 0],
            "timeToday": [163, 23598],
            "usn": -1,
        }

    def write_to_db[T](self, cursor: Cursor, timestamp: float, id_gen: SupportsNext[T]):
        if not isinstance(self.deck_id, int):
            raise TypeError(f"Deck .deck_id must be an integer, not {self.deck_id}.")
        if not isinstance(self.name, str):
            raise TypeError(f"Deck .name must be a string, not {self.name}.")

        (decks_json_str,) = cursor.execute("SELECT decks FROM col").fetchone()
        decks = json.loads(decks_json_str)
        decks.update({str(self.deck_id): self.to_json()})
        cursor.execute("UPDATE col SET decks = ?", (json.dumps(decks),))

        (models_json_str,) = cursor.execute("SELECT models from col").fetchone()
        models = json.loads(models_json_str)
        for note in self.notes:
            self.add_model(note.model)
        try:
            models.update(
                {
                    model.model_id: model.to_json(timestamp, self.deck_id)
                    for model in self.models.values()
                }
            )
        except:
            print("hi")
            raise

        cursor.execute("UPDATE col SET models = ?", (json.dumps(models),))

        for note in self.notes:
            note.write_to_db(cursor, timestamp, self.deck_id, id_gen)

    def write_to_file(self, file: str):
        """
        Write this deck to a .apkg file.
        """

        Package(self).write_to_file(file)

    def write_to_collection_from_addon(self):
        """
        Write to local collection. *Only usable when running inside an Anki addon!* Only tested on Anki 2.1.

        This writes to a temporary file and then calls the code that Anki uses to import packages.

        Note: the caller may want to use mw.checkpoint and mw.reset as follows:

          # creates a menu item called "Undo Add Notes From MyAddon" after this runs
          mw.checkpoint('Add Notes From MyAddon')
          # run import
          my_package.write_to_collection_from_addon()
          # refreshes main view so new deck is visible
          mw.reset()

        Tip: if your deck has the same name and ID as an existing deck, then the notes will get placed in that deck rather
        than a new deck being created.
        """

        Package(self).write_to_collection_from_addon()
