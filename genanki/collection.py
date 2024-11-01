from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import anki
import anki.lang
import anki.collection
import anki.decks
import anki.models
import anki.notes

import aqt
import aqt.profiles
import aqt.operations


def create_empty(dir: str):
    pth = Path(dir).resolve()
    base_folder = aqt.profiles.ProfileManager.get_created_base_folder(pth.as_posix())

    lang = anki.lang.get_def_lang()

    anki.lang.set_lang(lang[1])

    pm = aqt.profiles.ProfileManager(base_folder)
    pmLoadResult = pm.setupMeta()

    assert pmLoadResult.firstTime
    assert not pmLoadResult.loadError

    anki.collection.Collection.initialize_backend_logging()

    pm.create("User 1")
    pm.openProfile("User 1")

    return pm.collectionPath()


@contextmanager
def empty_collection(
    prefix: str | None = None,
    suffix: str | None = None,
    dir: str | None = None,
    delete: bool = True,
    ignore_cleanup_errors: bool = False,
):
    with TemporaryDirectory(
        prefix=prefix,
        suffix=suffix,
        dir=dir,
        delete=delete,
        ignore_cleanup_errors=ignore_cleanup_errors,
    ) as tmpdir:
        yield create_empty(tmpdir)
