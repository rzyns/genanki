import json
from sqlite3 import Cursor
from typing import Protocol

import anki
import anki.collection
import anki.lang
import anki.decks

# from .deck import Deck
from .model import Model
from .note import Note


if anki.lang.current_i18n is None:
    anki.lang.set_lang("en")


class SupportsNext[T](Protocol):
    def __next__(self) -> T: ...


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
