from abc import abstractmethod
from typing import Callable
import attr
import attrs

def test_factory():
    def some_factory[T](t: type[T]) -> Callable[[], list[T]]:
        return lambda: []

    @attrs.define
    class Foo:
        x: list[int] = attrs.field(default=[])
        y: list[int] = attrs.field(factory=some_factory(int))

    foo = Foo()
    bar = Foo()

    assert foo.x is bar.x
    assert foo.y is not bar.y

def test_stuff():
    assert attrs.Factory is attr.Factory

def test_property():
    @attrs.define
    class Foo:
        x: int
        _y: int = attrs.field(alias="y")

        @property
        def y(self) -> int:
            return self._y + 1
        
        @y.setter
        def y(self, value: str):
            if not isinstance(value, str):  # type: ignore
                raise ValueError("this should throw if the setter is called in the generated __init__ method")

    foo = Foo(x=1, y=1)
    assert foo._y == 1
    assert foo.y == 2

def test_method():

    class Foo:
        @abstractmethod
        def foo(self):
            pass

    class Bar(Foo):
        pass

    Bar().foo()
