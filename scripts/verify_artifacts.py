#!/usr/bin/env python3
"""Verify committed PDF/EPUB artifacts and Markdown copies.

This runs without a browser and complements the Playwright functional suite:

  python3 scripts/verify_artifacts.py

It checks that each edition has a plausible PDF (pages, outline, metadata),
a valid EPUB (mimetype, XML, no MathML, no raw <br>), and a Markdown copy
that matches its manuscript. Exit code 1 means at least one check failed.
"""

from __future__ import annotations

import re
import sys
import tomllib
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

errors: list[str] = []
notes: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def count_outline(items: list) -> int:
    total = 0
    for item in items:
        if isinstance(item, list):
            total += count_outline(item)
        else:
            total += 1
    return total


def nav_depth(element, depth: int = 0) -> int:
    """Maximum navPoint nesting depth in an EPUB NCX tree."""
    if element.tag.endswith("navPoint"):
        depth += 1
    return max([depth] + [nav_depth(child, depth) for child in element])


def verify_pdf(code: str, path: Path) -> None:
    check(path.is_file(), f"{code}: missing {path.relative_to(ROOT)}")
    if not path.is_file():
        return

    check(path.stat().st_size > 1_000_000, f"{code}: PDF is unexpectedly small")
    try:
        from pypdf import PdfReader
    except ImportError:
        errors.append("pypdf is not installed; run `pip install -r requirements.txt`")
        return

    reader = PdfReader(str(path))
    pages = len(reader.pages)
    bookmarks = count_outline(reader.outline)
    check(pages > 50, f"{code}: PDF has only {pages} pages")
    check(bookmarks > 100, f"{code}: PDF has only {bookmarks} bookmarks")
    check(reader.page_mode == "/UseOutlines", f"{code}: PDF does not open the outline panel")
    title = (reader.metadata.title if reader.metadata else "") or ""
    check(bool(title), f"{code}: PDF metadata has no title")
    notes.append(f"{code.upper()} PDF: {pages} pages, {bookmarks} bookmarks")


def verify_epub(code: str, path: Path) -> None:
    check(path.is_file(), f"{code}: missing {path.relative_to(ROOT)}")
    if not path.is_file():
        return

    check(path.stat().st_size > 100_000, f"{code}: EPUB is unexpectedly small")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        check(names and names[0] == "mimetype", f"{code}: EPUB mimetype is not the first entry")
        check(
            archive.read("mimetype") == b"application/epub+zip",
            f"{code}: EPUB mimetype is invalid",
        )
        check(any(name.endswith("cover.xhtml") for name in names), f"{code}: EPUB has no cover page")
        check(
            any("/fonts/" in name and name.endswith(".woff2") for name in names),
            f"{code}: EPUB has no embedded fonts",
        )

        parsed = 0
        for name in names:
            if not name.endswith((".xhtml", ".opf", ".ncx")):
                continue
            parsed += 1
            data = archive.read(name).decode("utf-8")
            try:
                ET.fromstring(data)
            except ET.ParseError as exc:
                errors.append(f"{code}: {name} is not valid XML: {exc}")
            check("<math" not in data, f"{code}: {name} still contains MathML")
            check(not re.search(r"<br\s*>", data), f"{code}: {name} contains an unclosed <br>")

        check(parsed > 10, f"{code}: EPUB has too few XML documents")

        chapter_files = [
            name for name in names
            if name.startswith("EPUB/text/ch") and name.endswith(".xhtml")
        ]
        check(
            len(chapter_files) > 25,
            f"{code}: EPUB is split by part, not by chapter ({len(chapter_files)} chapter files)",
        )

        nav_entries = 0
        outline_depth = 0
        try:
            ncx = ET.fromstring(archive.read("EPUB/toc.ncx"))
            nav_entries = sum(1 for node in ncx.iter() if node.tag.endswith("navPoint"))
            outline_depth = nav_depth(ncx)
        except (KeyError, ET.ParseError) as exc:
            errors.append(f"{code}: EPUB navigation is unreadable: {exc}")
        check(nav_entries > 100, f"{code}: EPUB TOC has only {nav_entries} entries")
        check(outline_depth >= 3, f"{code}: EPUB TOC is only {outline_depth} levels deep")

        notes.append(
            f"{code.upper()} EPUB: {parsed} XML docs, "
            f"{len(chapter_files)} chapter files, {nav_entries} TOC entries (depth {outline_depth})"
        )


def verify_markdown(code: str, source: Path) -> None:
    copy = DOCS / code / "dialectics.md"
    check(copy.is_file(), f"{code}: missing {copy.relative_to(ROOT)}")
    check(source.is_file(), f"{code}: missing manuscript {source.relative_to(ROOT)}")
    if copy.is_file() and source.is_file():
        check(copy.read_bytes() == source.read_bytes(), f"{code}: dialectics.md is out of date")


def verify_privacy() -> None:
    offenders = []
    for path in DOCS.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".css", ".js", ".md", ".json", ".xml", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "/Users/" in text or "qliu23" in text:
            offenders.append(str(path.relative_to(ROOT)))
    check(not offenders, f"local paths leaked into docs: {', '.join(offenders[:5])}")


def main() -> int:
    config = tomllib.loads((ROOT / "book.toml").read_text(encoding="utf-8"))
    for code, meta in config["editions"].items():
        verify_pdf(code, DOCS / code / "dialectics.pdf")
        verify_epub(code, DOCS / code / "dialectics.epub")
        verify_markdown(code, ROOT / meta["source"])

    verify_privacy()

    for note in notes:
        print(f"  {note}")
    if errors:
        print("\nArtifact verification failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Artifact verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
