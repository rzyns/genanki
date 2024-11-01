import attrs


@attrs.define
class Card:
    ord: int = attrs.field()
    suspend: bool = attrs.field(default=False)
