from typing import Any
import anki
import anki.collection
import anki.models
import anki.lang
import anki.decks

from attrs import define, field

# from .deck import Deck
from genanki.model import Model
from genanki.note import Note


if anki.lang.current_i18n is None:
    anki.lang.set_lang("en")


@define(kw_only=True)
class Deck:
    name: str
    description: str = field(default="An Anki deck")
    notes: list[Note[Any]] = field(default=[])
    models: dict[str, Model[Any]] = field(default={})
    deck_id: anki.decks.DeckId = field(default=anki.decks.DeckId(0))

    def add_note(self, note: Note[Any]) -> None:
        if note.model.name not in self.models:
            self.add_model(note.model)
        elif note.model != self.models[note.model.name]:
            raise ValueError("Note model does not match deck model")

        self.notes.append(note)

    def add_model(self, model: Model[Any]):
        self.models[model.name] = model

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
