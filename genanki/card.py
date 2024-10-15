from sqlite3 import Cursor
from typing import Protocol


class SupportsNext[T](Protocol):
    def __next__(self) -> T: ...


class Card:
    def __init__(self, ord_: int, suspend: bool = False):
        self.ord = ord_
        self.suspend = suspend

    def write_to_db[T](
        self,
        cursor: Cursor,
        timestamp: float,
        deck_id: int,
        note_id: int,
        id_gen: SupportsNext[T],
        due: int = 0,
    ):
        queue = -1 if self.suspend else 0

        params = (
            next(id_gen),    # id
            note_id,         # nid
            deck_id,         # did
            self.ord,        # ord
            int(timestamp),  # mod
            -1,              # usn
            0,               # type (=0 for non-Cloze)
            queue,           # queue
            due,             # due
            0,               # ivl
            0,               # factor
            0,               # reps
            0,               # lapses
            0,               # left
            0,               # odue
            0,               # odid
            0,               # flags
            "",              # data
        )

        _ = cursor.execute(
            "INSERT INTO cards VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);", params
        )
