#!/usr/bin/env python3
"""PDF 后处理：写入阅读器侧边栏的书签（大纲）。

Chromium 的 print-to-pdf 不会生成 PDF 书签。这里用 pypdf 读回生成的 PDF，
借助 Chromium 写入的命名目标（每章标题的 id）定位首页，再写入嵌套书签。

依赖 pypdf（`pip install pypdf`）。缺少依赖时调用方应跳过这一步。
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path


def available() -> bool:
    try:
        import pypdf  # noqa: F401
    except ImportError:
        return False
    return True


def normalize(text: str) -> str:
    """去掉空白并做 NFKC 归一，抵消 PDF 提取时的空格、换行与康熙部首。"""
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", "", text)


def locate_pages(
    pdf_path: Path,
    entries: list[tuple[str, str, str | None]],
    header: str = "",
) -> dict[str, int]:
    """找出每个标题所在页，返回 {slug: 页码(从 1 开始)}。

    首选 Chromium 打印时写入的命名目标（每个标题的 id 都在里面），几乎零成本；
    缺失的条目再用文本搜索兜底（目录页先靠页眉过滤掉）。
    """
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    pages: dict[str, int] = {"cover": 1}

    try:
        named = reader.named_destinations
    except Exception:  # noqa: BLE001 - 结构异常时退回文本搜索
        named = {}

    for slug, _title, _parent in entries:
        dest = named.get(f"/{slug}")
        if dest is None:
            continue
        try:
            index = reader.get_destination_page_number(dest)
        except Exception:  # noqa: BLE001
            index = None
        if index is not None and index >= 0:
            pages[slug] = index + 1

    # 目录页没有命名目标，取前几页里以「目录」开头的一页
    if "toc" not in pages:
        for index in range(min(6, len(reader.pages))):
            if normalize(reader.pages[index].extract_text() or "").startswith("目录"):
                pages["toc"] = index + 1
                break

    if all(slug in pages for slug, _title, _parent in entries):
        return pages

    # 按行归一化后匹配行首，避免把正文里顺带提到的标题误当成小节起点
    line_pages: list[list[str]] = []
    joined: list[str] = []
    for page in reader.pages:
        lines = [normalize(line).lstrip("★") for line in (page.extract_text() or "").splitlines()]
        lines = [line for line in lines if line]
        line_pages.append(lines)
        joined.append("".join(lines))

    needle_header = normalize(header)

    def search(needle: str, require_header: bool, start: int) -> int | None:
        for index in range(start, len(line_pages)):
            if require_header and needle_header and needle_header not in joined[index]:
                continue
            for line in line_pages[index]:
                if line.startswith(needle):
                    return index
            # 长标题被行宽折断时，首行会以标题前缀的形式出现
            if len(needle) > 12:
                for line in line_pages[index]:
                    if len(line) >= 10 and needle.startswith(line):
                        return index
        return None

    cursor = 0
    for slug, title, _parent in entries:
        if slug in pages:
            cursor = max(cursor, pages[slug] - 1)
            continue
        needle = normalize(title)
        if not needle:
            continue
        found = search(needle, True, cursor)
        if found is None:
            found = search(needle, False, cursor)
        if found is None and len(needle) > 12:
            found = search(needle[:12], False, cursor)
        if found is not None:
            pages[slug] = found + 1
            cursor = found
    return pages


def add_outline(
    pdf_path: Path,
    entries: list[tuple[str, str, str | None]],
    pages: dict[str, int],
    title: str = "",
    author: str = "",
) -> bool:
    """把目录写进 PDF 书签，并让阅读器默认打开书签面板。"""
    from pypdf import PdfWriter

    if not pages:
        return False

    writer = PdfWriter(clone_from=str(pdf_path))
    nodes: dict[str, object] = {}
    for slug, name, parent in entries:
        page = pages.get(slug)
        if not page or page > len(writer.pages):
            continue
        node = writer.add_outline_item(name, page - 1, parent=nodes.get(parent) if parent else None)
        nodes[slug] = node

    writer.page_mode = "/UseOutlines"
    meta = {"/Title": title} if title else {}
    if author:
        meta["/Author"] = author
    if meta:
        writer.add_metadata(meta)

    tmp = pdf_path.with_name(pdf_path.stem + ".outline.pdf")
    with tmp.open("wb") as handle:
        writer.write(handle)
    tmp.replace(pdf_path)
    return True
