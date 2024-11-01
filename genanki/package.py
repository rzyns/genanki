from pathlib import Path
from typing import Protocol
from collections.abc import Iterable

import anki
import anki.lang
import anki.collection
import anki.decks
import anki.models
import anki.notes
# from anki.exporting import AnkiPackageExporter
from anki.import_export_pb2 import ExportAnkiPackageOptions

from genanki import collection

from .deck import Deck

class SupportsNext[T](Protocol):
    def __next__(self) -> T: ...


class Package:
    decks: list[Deck]
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
        root = Path(__file__).parent.parent.resolve()

        with collection.empty_collection(dir=root.as_posix()) as collection_path:
            col = anki.collection.Collection(collection_path)
            for genanki_deck in self.decks:
                anki_deck = col.decks.new_deck()
                anki_deck.name = genanki_deck.name

                out = col.decks.add_deck(anki_deck)
                genanki_deck.deck_id = anki.decks.DeckId(out.id)

                for m in genanki_deck.models.values():
                    a = col._backend.add_notetype(m.req)
                    assert a.id is not None
                    m.model_id = anki.models.NotetypeId(a.id)

                    for a in genanki_deck.notes:
                        col._backend.add_note(
                            deck_id=genanki_deck.deck_id,
                            note=a.req,
                        )

                col.export_anki_package(
                    out_path=file,
                    options=ExportAnkiPackageOptions(
                        with_deck_configs=True,
                        with_media=True,
                        with_scheduling=True,
                    ),
                    limit=None,
                )
