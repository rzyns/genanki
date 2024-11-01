import sqlite3
from collections.abc import Sequence
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, cast
from zipfile import ZipFile

import anki
import anki.collection
import anki.decks
import anki.lang
import anki.models
import aqt.profiles
import pyzstd

from genanki import Package, builtin_models
from genanki.deck import Deck
from genanki.model import FieldSpec, Model, ModelSpec, TemplateSpec, field, spec, template
from genanki.note import Note
from genanki.util import guid_for
from tests.db_types import notetypes


def extract_anki_data(file: str):
    def dict_factory(cursor: sqlite3.Cursor, row: Sequence[Any]):
        fields = [column[0] for column in cursor.description]
        return {key: value for key, value in zip(fields, row)}

    conn = sqlite3.connect(file)
    conn.row_factory = dict_factory
    curs = conn.cursor()
    curs.execute("SELECT tbl_name from sqlite_master WHERE type='table'")

    tables = cast(list[dict[str, Any]], curs.fetchall())

    out: dict[str, Any] = {}

    for row in tables:
        table_name = row["tbl_name"]
        if table_name != "tags":
            curs.execute(f"SELECT * FROM {table_name}")
            out[table_name] = curs.fetchall()

    conn.close()

    return out


def get_package_file_data(pkg: Package):
    root = Path(__file__).parent.parent.resolve()

    with NamedTemporaryFile(dir=root, suffix=".apkg") as file:
        pkg.write_to_file(file.name)

        zf = ZipFile(file.name)

        with NamedTemporaryFile(dir=root, suffix=".sqlite3") as tmp:
            try:
                fp = zf.open("collection.anki21b")
                tmp.write(pyzstd.decompress(fp.read()))
            except KeyError:
                fp = zf.open("collection.anki21")
                tmp.write(fp.read())

            return extract_anki_data(tmp.name)

def create_anki_base(pth: Path):
    base_folder = aqt.profiles.ProfileManager.get_created_base_folder(pth.as_posix())

    # default to specified/system language before getting user's preference so that we can localize some more strings
    lang = anki.lang.get_def_lang()
    anki.lang.set_lang(lang[1])
    # i18n_setup = True

    pm = aqt.profiles.ProfileManager(base_folder)
    pmLoadResult = pm.setupMeta()

    assert pmLoadResult.firstTime
    assert not pmLoadResult.loadError

    anki.collection.Collection.initialize_backend_logging()

    pm.create("User 1")
    pm.openProfile("User 1")
    collection_path = pm.collectionPath()

    return anki.collection.Collection(collection_path)


@contextmanager
def open_pkg_collection_sqlite3(pkg: Package):
    with NamedTemporaryFile(suffix=".apkg") as tmp:
        with NamedTemporaryFile(suffix=".sqlite3") as tmp2:
            pkg.write_to_file(tmp.name)

            zf = ZipFile(tmp.name)

            try:
                fp = zf.open("collection.anki21b")
                tmp2.write(pyzstd.decompress(fp.read()))
            except KeyError:
                fp = zf.open("collection.anki21")
                tmp2.write(fp.read())

            yield sqlite3.connect(tmp2.name)
            


def test_guid():
    assert builtin_models.BASIC_MODEL.fields[builtin_models.BASIC_MODEL.sort_field_index]

    class SomeNote(Note):
        @property
        def guid(self) -> str:
            return guid_for("THE NOTE GUID")

    assert SomeNote.model
    assert SomeNote(model=builtin_models.BASIC_MODEL, fields=builtin_models.BASIC_MODEL.model_spec.fields(Front="", Back=""))._guid is None
    assert SomeNote(model=builtin_models.BASIC_MODEL, fields=builtin_models.BASIC_MODEL.model_spec.fields(Front="", Back="")).guid == guid_for("THE NOTE GUID")

    assert SomeNote(model=builtin_models.BASIC_MODEL, fields=builtin_models.BASIC_MODEL.model_spec.fields(Front="", Back=""), guid="foo")._guid == "foo"
    assert SomeNote(model=builtin_models.BASIC_MODEL, fields=builtin_models.BASIC_MODEL.model_spec.fields(Front="", Back=""), guid="foo").guid == guid_for("THE NOTE GUID")

    assert Note(model=builtin_models.BASIC_MODEL, fields=builtin_models.BASIC_MODEL.model_spec.fields(Front="", Back=""))._guid is None
    assert Note(model=builtin_models.BASIC_MODEL, fields=builtin_models.BASIC_MODEL.model_spec.fields(Front="", Back=""), guid="foo").guid == "foo"


class ZippieModelSpec(ModelSpec[FieldSpec]):
    @spec
    class fields(FieldSpec):
        Zippie: str = field()

    @spec
    class templates(TemplateSpec[Any], fields=fields):
        front_back: str = template({
            "qfmt": "{{Zippie}}",
            "afmt": "{{FrontSide}} zop"
        })


def test_package():
    d = Deck(name="foo", description="bar")
    m = Model(
        # model_id=anki.models.NotetypeId(123),
        name="baz",
        model_spec=ZippieModelSpec,
    )
    d.add_model(m)

    class SomeNote(Note):
        @property
        def guid(self) -> str:
            return guid_for("THE NOTE GUID")

    n = SomeNote(
        model=m,
        fields=ZippieModelSpec.fields(Zippie="Zop"),
        due=0,
    )

    d.add_note(n)
    p = Package(d)

    data = get_package_file_data(p)

    assert len(data["col"]) == 1

    [ mod ] = filter(lambda x: x.name == m.name, map(lambda x: notetypes.model_validate(x), list(data["notetypes"])))
    assert mod
    assert m.name in map(lambda x: x["name"], data["notetypes"])

    # assert n.model.model_id in list(map(lambda x: x["mid"], data["notes"]))
    # assert len(data["notes"]) == 1
    assert n.guid in list(map(lambda x: x["guid"], data["notes"]))
