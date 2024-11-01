from pathlib import Path
from zipfile import ZipFile

import pyzstd

import tyro

def main(
    file: Path,
    /,
    output: Path | None = None
):
    if not file.exists():
        raise FileNotFoundError(file)

    with ZipFile(file) as zip_file:
        info = zip_file.getinfo("collection.anki21b")
        with zip_file.open(info) as fp:
            data = pyzstd.decompress(fp.read())

            if output is None:
                output = Path.cwd() / file.with_suffix(".sqlite3").name
            
            with output.open("wb") as fp:
                fp.write(data)

if __name__ == "__main__":
    tyro.cli(main)
