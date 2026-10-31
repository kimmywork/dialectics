#!/usr/bin/env python3
"""《走出二选一》/ Beyond Either/Or 发布框架。

一条命令把两种语言的产物写进 docs/：
  • docs/index.html       双语落地页（按浏览器语言自动切换）
  • docs/zh/*.html|pdf|epub
  • docs/en/*.html|pdf|epub

用法：
  python3 build.py            # 全量构建
  python3 build.py --no-pdf   # 网页 + EPUB
  python3 build.py --no-epub  # 网页 + PDF
  python3 build.py --clean    # 删除生成物
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "docs"
ASSETS = SITE / "assets"
BUILD = ROOT / "build"
MARKDOWN = ROOT / "markdown"

CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
          "八": 8, "九": 9, "十": 10}
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
         "VIII": 8, "IX": 9, "X": 10}

UI = {
    "zh": {
        "skip": "跳到正文",
        "menu_open": "打开目录",
        "menu_close": "关闭目录",
        "theme": "切换深色 / 浅色",
        "cover_toc": "封面与目录",
        "contents": "目录",
        "start": "开始阅读",
        "pdf": "PDF",
        "epub": "ePub",
        "prev": "← 上一章",
        "next": "下一章 →",
        "github": "GitHub 源码",
        "lang_switch": "English",
        "hero_kicker": "辩证思维手册",
        "cover_kicker": "辩证思维手册",
        "cover_foot": "走出非黑即白 · 看清问题的结构",
        "toc": "目录",
        "colophon": "本书说明",
        "colophon_labels": {
            "title": "书名", "author": "作者", "edition": "版本", "online": "在线版",
            "source": "源码", "license": "许可", "typeset": "排版", "typeface": "字体",
        },
        "typeset": "Markdown → pandoc → Chromium 打印引擎",
        "colophon_note": "本书为《{title}》的排版版本，正文内容以 Markdown 源文件为准。",
        "stats_parts": "个部分",
        "stats_chapters": "章",
        "stats_words": "万字",
        "typeface": "Newsreader / Noto Serif SC",
        "deep_dive": "进阶深潜",
        "guide_marker": "全书结构与章节行动导览",
        "cover": "封面",
        "resume": "继续上次阅读",
        "ai_read": "✦ AI 帮我读",
        "ai_copied": "本章提示词已复制，去 AI 对话粘贴即可",
        "ai_failed": "复制失败，请手动选择提示词复制",
    },
    "en": {
        "skip": "Skip to content",
        "menu_open": "Open table of contents",
        "menu_close": "Close table of contents",
        "theme": "Toggle dark / light theme",
        "cover_toc": "Cover & Contents",
        "contents": "Contents",
        "start": "Start reading",
        "pdf": "PDF",
        "epub": "ePub",
        "prev": "← Previous chapter",
        "next": "Next chapter →",
        "github": "GitHub source",
        "lang_switch": "中文",
        "hero_kicker": "A Practical Handbook",
        "cover_kicker": "A Practical Handbook",
        "cover_foot": "Beyond the false choice · See the structure of the problem",
        "toc": "Contents",
        "colophon": "About This Book",
        "colophon_labels": {
            "title": "Title", "author": "Author", "edition": "Edition", "online": "Online",
            "source": "Source", "license": "License", "typeset": "Typeset", "typeface": "Typeface",
        },
        "typeset": "Markdown → pandoc → Chromium print pipeline",
        "colophon_note": "This is a typeset edition of “{title}”. The Markdown source is the authoritative text.",
        "stats_parts": "parts",
        "stats_chapters": "chapters",
        "stats_words": "words",
        "typeface": "Newsreader / Noto Serif SC",
        "deep_dive": "Deep Dive",
        "guide_marker": "Master Table of Contents",
        "cover": "Cover",
        "resume": "Continue reading",
        "ai_read": "✦ Read with AI",
        "ai_copied": "Chapter prompt copied. Paste it into any AI chat.",
        "ai_failed": "Copy failed — please copy the prompt manually.",
    },
}


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #

def log(msg: str) -> None:
    print(f"\033[2m•\033[0m {msg}", flush=True)


def step(msg: str) -> None:
    print(f"\n\033[1;38;5;130m▸ {msg}\033[0m", flush=True)


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def die(msg: str) -> None:
    print(f"\033[31m错误：{msg}\033[0m", file=sys.stderr)
    raise SystemExit(1)


def find_pandoc() -> str:
    exe = shutil.which("pandoc")
    if not exe:
        die("找不到 pandoc，请先安装（brew install pandoc）")
    return exe


def pandoc_md_to_html(exe: str, markdown: str) -> str:
    if not markdown.strip():
        return ""
    proc = subprocess.run(
        [exe, "--from=markdown+smart+lists_without_preceding_blankline",
         "--to=html5", "--mathml", "--wrap=none", "--no-highlight"],
        input=markdown, capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        die(f"pandoc 渲染失败：{proc.stderr.strip()}")
    return tidy(proc.stdout.strip())


def tidy(fragment: str) -> str:
    """收拾 pandoc 输出：去掉标题前后的分隔线，给宽表格加滚动容器。"""
    def _heading(match: re.Match[str]) -> str:
        inner = match.group(2)
        for tag in ("[进阶深潜]", "[Deep Dive]"):
            inner = inner.replace(tag, f'<span class="tag-advanced">{tag[1:-1]}</span>')
        inner = re.sub(r"^★\s*", '<span class="star">★</span> ', inner)
        return match.group(1) + inner + match.group(3)

    fragment = re.sub(r"(<h[1-6][^>]*>)(.*?)(</h[1-6]>)", _heading, fragment, flags=re.S)
    fragment = re.sub(r"<hr\s*/?>\s*(?=<h[1-6])", "", fragment)
    fragment = re.sub(r"(</h[1-6]>)\s*<hr\s*/?>", r"\1", fragment)
    fragment = re.sub(r"^(?:\s*<hr\s*/?>\s*)+", "", fragment)
    fragment = re.sub(r"(?:\s*<hr\s*/?>)+\s*$", "", fragment)
    fragment = re.sub(
        r"<table(?![^>]*class=)[^>]*>.*?</table>",
        lambda m: f'<div class="table-wrap">{m.group(0)}</div>',
        fragment, flags=re.S,
    )
    return fragment.strip()


def title_html(title: str) -> str:
    """章节标题里允许 *斜体*，转成 HTML；其余内容做转义。"""
    parts = re.split(r"(\*[^*]+\*)", title)
    out = []
    for part in parts:
        if len(part) > 2 and part.startswith("*") and part.endswith("*") and not part.startswith("**"):
            out.append(f"<em>{esc(part[1:-1])}</em>")
        else:
            out.append(esc(part))
    return "".join(out)


def title_text(title: str) -> str:
    return re.sub(r"[*]", "", title)


def plain_text(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def render(template: str, **values: str) -> str:
    def sub(match: re.Match[str]) -> str:
        return values.get(match.group(1), "")
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", sub, template)


# --------------------------------------------------------------------------- #
# 书籍结构
# --------------------------------------------------------------------------- #

@dataclass
class Chapter:
    title: str
    body_md: str
    part: "Part | None" = None
    slug: str = ""
    body: str = ""
    label: str = ""
    name: str = ""
    subtitle: str = ""
    starred: bool = False
    sections: list[tuple[str, str]] = field(default_factory=list)

    @property
    def full_title(self) -> str:
        base = title_text(self.title)
        return f"{base}（{self.subtitle}）" if self.subtitle else base

    @property
    def kicker(self) -> str:
        return self.part.label if self.part else ""

    @property
    def page(self) -> str:
        return f"{self.slug}.html"


@dataclass
class Part:
    title: str
    intro_md: str
    chapters: list[Chapter] = field(default_factory=list)
    slug: str = ""
    label: str = ""
    name: str = ""
    intro: str = ""

    @property
    def page(self) -> str:
        return f"{self.slug}.html"

    @property
    def full_title(self) -> str:
        return f"{self.label} {self.name}".strip()


@dataclass
class Book:
    code: str
    lang: str
    title: str
    meta: dict
    parts: list[Part]
    loose: list[Chapter]

    @property
    def ui(self) -> dict:
        return UI[self.code]

    @property
    def flow(self) -> list[Part | Chapter]:
        items: list[Part | Chapter] = list(self.loose)
        for part in self.parts:
            items.append(part)
            items.extend(part.chapters)
        return items

    @property
    def chapters(self) -> list[Chapter]:
        out = list(self.loose)
        for part in self.parts:
            out.extend(part.chapters)
        return out

    def stats(self) -> str:
        numbered = sum(1 for p in self.parts if p.label.startswith("第") or p.label.startswith("Part"))
        chaps = sum(1 for c in self.chapters if c.title.startswith("第") or c.title.startswith("Chapter"))
        ui = self.ui
        if self.code == "zh":
            chars = len(re.findall(r"[\u4e00-\u9fff]", self.meta["_source_text"]))
            return f"{numbered} {ui['stats_parts']} · {chaps} {ui['stats_chapters']} · 约 {chars / 10000:.0f} {ui['stats_words']}"
        words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-]*", self.meta["_source_text"]))
        return f"{numbered} {ui['stats_parts']} · {chaps} {ui['stats_chapters']} · ~{words / 1000:.0f}k {ui['stats_words']}"


def split_subtitle(title: str) -> tuple[str, str]:
    """把标题末尾的「（如何……）」或「(How ...)」拆成副标题。"""
    match = re.match(r"^(.*?)[（(]([^（）()]*)[）)]\s*$", title.strip())
    if match and len(match.group(1)) > 4:
        return match.group(1).strip(), match.group(2).strip()
    return title.strip(), ""


def split_label(title: str) -> tuple[str, str]:
    if title.strip() in {"附录", "正文", "目录", "Appendices", "Appendix", "Contents"}:
        return title.strip(), ""
    match = re.match(
        r"^((?:第\s*\d+\s*章)|(?:第[一二三四五六七八九十]+部分)|(?:附录\s*[A-Za-z])|"
        r"(?:Chapter\s+\d+)|(?:Part\s+[IVXL]+)|(?:Appendix\s+[A-Za-z])|"
        r"序章|结语|前言|Preface|Prologue|Epilogue)\s*(.*)$",
        title,
    )
    if match:
        name = re.sub(r"^[：:、，,\s]+", "", match.group(2).strip())
        return match.group(1).strip(), name
    return "", title


def slugify_chapter(title: str, index: int) -> str:
    if title.startswith(("前言", "Preface")):
        return "preface"
    if title.startswith(("序章", "Prologue")):
        return "prologue"
    if title.startswith(("结语", "Epilogue")):
        return "epilogue"
    if m := re.match(r"^第\s*(\d+)\s*章", title):
        return f"ch{int(m.group(1)):02d}"
    if m := re.match(r"^Chapter\s+(\d+)", title):
        return f"ch{int(m.group(1)):02d}"
    if m := re.match(r"^附录\s*([A-Za-z])", title):
        return f"appendix-{m.group(1).lower()}"
    if m := re.match(r"^Appendix\s+([A-Za-z])", title):
        return f"appendix-{m.group(1).lower()}"
    return f"ch{index:02d}-x"


def slugify_part(title: str, index: int) -> str:
    if m := re.match(r"^第([一二三四五六七八九十]+)部分", title):
        return f"part-{CN_NUM.get(m.group(1), index)}"
    if m := re.match(r"^Part\s+([IVXL]+)", title):
        return f"part-{ROMAN.get(m.group(1), index)}"
    if title.startswith(("附录", "Appendices", "Appendix")):
        return "appendix"
    return f"part-{index}"


def parse_book(path: Path, code: str, lang: str) -> Book:
    text = path.read_text(encoding="utf-8")
    stray = re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text)
    if stray:
        log(f"警告：{path.name} 里有 {len(stray)} 个控制字符，可能有 LaTeX 被转义。")

    title = ""
    segments: list[dict] = []
    for line in text.split("\n"):
        if m := re.match(r"^(#{1,2})\s+(.+?)\s*$", line):
            level = len(m.group(1))
            if level == 1 and not title:
                title = m.group(2)
                continue
            segments.append({"level": level, "title": m.group(2), "lines": []})
        elif segments:
            segments[-1]["lines"].append(line)

    parts: list[Part] = []
    loose: list[Chapter] = []
    current: Part | None = None
    part_index = chapter_index = 0

    for seg in segments:
        body = "\n".join(seg["lines"]).strip()
        starred = bool(re.match(r"^★\s*", seg["title"]))
        raw_title = re.sub(r"^★\s*", "", seg["title"])
        if seg["level"] == 1:
            part_index += 1
            label, name = split_label(raw_title)
            current = Part(
                title=raw_title, intro_md=body,
                slug=slugify_part(raw_title, part_index),
                label=label or raw_title, name=name,
            )
            parts.append(current)
        else:
            chapter_index += 1
            title_text, subtitle = split_subtitle(raw_title)
            label, name = split_label(title_text)
            chapter = Chapter(
                title=title_text, subtitle=subtitle, body_md=body,
                slug=slugify_chapter(title_text, chapter_index),
                label=label, name=name, starred=starred,
            )
            if current is not None:
                chapter.part = current
                current.chapters.append(chapter)
            else:
                loose.append(chapter)

    if not parts and not loose:
        die(f"没有从 {path} 里解析出任何章节标题")

    return Book(code=code, lang=lang, title=title,
                meta={"_path": str(path), "_source_text": text},
                parts=parts, loose=loose)


# --------------------------------------------------------------------------- #
# 页面片段
# --------------------------------------------------------------------------- #

def nav_html(book: Book, current: str) -> str:
    ui = book.ui
    rows = [f'<a class="nav-cover{" is-active" if current == "index" else ""}" '
            f'href="index.html">{ui["cover_toc"]}</a>']

    def chapter_row(ch: Chapter) -> str:
        active = " is-active" if current == ch.slug else ""
        aria = ' aria-current="page"' if current == ch.slug else ""
        num = ch.label or ""
        star = '<span class="nav-star" title="★">★</span>' if ch.starred else ""
        sub = f'<span class="nav-sub">{esc(ch.subtitle)}</span>' if ch.subtitle else ""
        return (f'<li><a class="nav-item{active}" href="{ch.page}"{aria} '
                f'title="{esc(ch.full_title)}">'
                f'<span class="nav-num">{esc(num)}</span>'
                f'<span class="nav-name"><span class="nav-main">{esc(title_text(ch.name or ch.title))}</span>'
                f'{sub}</span>{star}</a></li>')

    for ch in book.loose:
        rows.append(f'<div class="nav-solo"><ol class="nav-list">{chapter_row(ch)}</ol></div>')

    for part in book.parts:
        active = " is-active" if current == part.slug else ""
        rows.append('<div class="nav-part">')
        rows.append(
            f'<a class="nav-part-title{active}" href="{part.page}">'
            f'<span class="nav-part-label">{esc(part.label)}</span>'
            f'<span class="nav-part-name">{esc(part.name)}</span></a>'
        )
        rows.append('<ol class="nav-list">')
        rows.extend(chapter_row(ch) for ch in part.chapters)
        rows.append("</ol></div>")
    return "\n".join(rows)


def pager_html(book: Book, current: str) -> str:
    flow = book.flow
    order = [item.slug for item in flow]
    if current not in order:
        return ""
    idx = order.index(current)
    prev_item = flow[idx - 1] if idx > 0 else None
    next_item = flow[idx + 1] if idx + 1 < len(flow) else None
    ui = book.ui

    def card(item, direction: str) -> str:
        if item is None:
            return '<span class="pager-card is-empty"></span>'
        return (f'<a class="pager-card pager-{direction}" href="{item.page}">'
                f'<span class="pager-dir">{ui["prev"] if direction == "prev" else ui["next"]}</span>'
                f'<span class="pager-title">{esc(item.full_title)}</span></a>')

    return (f'<nav class="pager" aria-label="pager">{card(prev_item, "prev")}'
            f'{card(next_item, "next")}</nav>')


def part_page_html(part: Part) -> str:
    head = f'<p class="part-label">{esc(part.label)}</p>'
    if part.name:
        head += f'<h1 class="part-title">{esc(part.name)}</h1>'
    else:
        head = f'<h1 class="part-title">{esc(part.label)}</h1>'

    intro = (f'<div class="prose part-intro">{part.intro}</div>' if part.intro
             else '<div class="part-intro part-intro-empty" aria-hidden="true"></div>')
    items = []
    for n, ch in enumerate(part.chapters, 1):
        star = '<span class="star" title="★">★</span>' if ch.starred else ""
        sub = f'<span class="part-ch-sub">{esc(ch.subtitle)}</span>' if ch.subtitle else ""
        items.append(
            f'<li><a href="{ch.page}"><span class="part-ch-num">{n:02d}</span>'
            f'<span class="part-ch-title">{title_html(ch.title)}{star}{sub}</span>'
            f'<span class="part-ch-arrow">→</span></a></li>'
        )
    listing = f'<ol class="part-chapters">{"".join(items)}</ol>' if items else ""
    return f'<article class="part-page">{head}{intro}{listing}</article>'


def chapter_page_html(ch: Chapter, book: Book, site_url: str) -> str:
    kicker = f'<p class="kicker">{esc(ch.kicker)}</p>' if ch.kicker else ""
    star = '<span class="star" title="★">★</span> ' if ch.starred else ""
    sub = f'<p class="chapter-sub">{esc(ch.subtitle)}</p>' if ch.subtitle else ""
    url = f"{site_url}/{book.code}/{ch.page}"
    if book.code == "zh":
        prompt = (f"帮我解读这本《{book.meta['full_title']}》的这一章内容：\n"
                  f"《{ch.title}》\n{url}\n使用结构化的分析方法。")
    else:
        prompt = (f'Help me interpret this chapter from "{book.meta["full_title"]}":\n'
                  f'"{ch.title}"\n{url}\nUse a structured analytical approach.')
    ai = (f'<div class="ai-read chapter-ai">'
          f'<button class="btn btn-ai" data-ai-copy data-prompt="{esc(prompt).replace(chr(10), "&#10;")}" '
          f'data-toast="{esc(book.ui["ai_copied"])}" data-fail="{esc(book.ui["ai_failed"])}">'
          f'{book.ui["ai_read"]}</button>'
          f'<span class="ai-status" role="status" aria-live="polite" hidden></span></div>')
    return (f'<article class="chapter">{kicker}'
            f'<header class="chapter-head"><h1>{star}{title_html(ch.title)}</h1>{sub}</header>'
            f'{ai}<div class="prose">{ch.body}</div></article>')


def style_guide_section(fragment: str, marker: str) -> str:
    found = re.search(rf'<h3 id="[^"]*{re.escape(marker)}[^"]*"[^>]*>', fragment)
    if not found:
        return fragment
    head, tail = fragment[:found.start()], fragment[found.start():]
    tail = re.sub(
        r'<li><strong>(.*?)</strong>\s*([^<]+?)(?=\s*(?:<ul>|</li>))',
        r'<li class="guide-item"><strong>\1</strong>'
        r'<span class="guide-desc">\2</span>',
        tail, flags=re.S,
    )
    return head + tail


def extract_sections(fragment: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for match in re.finditer(r'<h3 id="([^"]+)"[^>]*>(.*?)</h3>', fragment, flags=re.S):
        inner = re.sub(r'<span class="star"[^>]*>.*?</span>', "", match.group(2))
        title = plain_text(inner)
        if title:
            out.append((match.group(1), title))
    return out


def chapter_description(ch: Chapter) -> str:
    text = plain_text(ch.body)
    return text[:110] + "…" if len(text) > 110 else text


def catalog_html(book: Book) -> str:
    def title(ch: Chapter) -> str:
        sub = f'<span class="catalog-sub">{esc(ch.subtitle)}</span>' if ch.subtitle else ""
        return f'<span class="catalog-main">{esc(ch.name or ch.title)}</span>{sub}'

    def star(ch: Chapter) -> str:
        return '<span class="catalog-star" title="★">★</span>' if ch.starred else ""

    blocks = []
    for ch in book.loose:
        blocks.append(
            f'<div class="catalog-solo"><a href="{ch.page}">'
            f'<span class="catalog-label">{esc(ch.label)}</span>'
            f'<span class="catalog-title">{title(ch)}</span>{star(ch)}</a></div>'
        )
    for part in book.parts:
        entries = "".join(
            f'<li><a href="{ch.page}"><span class="catalog-num">{esc(ch.label)}</span>'
            f'<span class="catalog-title">{title(ch)}</span>{star(ch)}</a></li>'
            for ch in part.chapters
        )
        blocks.append(
            f'<div class="catalog-part">'
            f'<a class="catalog-part-head" href="{part.page}">'
            f'<span class="catalog-label">{esc(part.label)}</span>'
            f'<span class="catalog-part-name">{esc(part.name)}</span></a>'
            f'<ol class="catalog-chapters">{entries}</ol></div>'
        )
    return "\n".join(blocks)


# --------------------------------------------------------------------------- #
# 网页
# --------------------------------------------------------------------------- #

def font_cdn_html(cfg: dict) -> str:
    base = cfg.get("fonts", {}).get("chinese_cdn", "").rstrip("/")
    if not base:
        return ""
    weights = [400]
    if cfg.get("fonts", {}).get("web_bold"):
        weights.append(700)
    links = "\n".join(f'<link rel="stylesheet" href="{base}/{w}.css">' for w in weights)
    return '<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>\n' + links


def build_site(book: Book, cfg: dict, fonts: dict, asset_version: str = "") -> dict[str, str]:
    layout = (ROOT / "templates" / "layout.html").read_text(encoding="utf-8")
    meta = book.meta
    ui = book.ui
    full_title = meta["full_title"]
    description = meta["description"]
    author = meta.get("author", "").strip()
    homepage = meta.get("homepage", "").strip()
    author_html = (f'<a href="{homepage}">{esc(author)}</a>'
                   if author and homepage else esc(author))
    license_name = meta.get("license", "")
    license_url = meta.get("license_url", "")
    repo_url = meta.get("repo", "")
    pdf_name = "dialectics.pdf"
    epub_name = "dialectics.epub"
    other = "en" if book.code == "zh" else "zh"
    site_url = cfg["site"]["url"].rstrip("/")
    og_locale = "zh_CN" if book.code == "zh" else "en_US"
    og_locale_alt = "en_US" if book.code == "zh" else "zh_CN"
    og_image = f"{site_url}/assets/share/{book.code}.png"

    font_preload = ""
    if fonts.get("newsreader", {}).get((400, "normal")):
        font_preload = ('<link rel="preload" href="../assets/fonts/newsreader-400.woff2" '
                        'as="font" type="font/woff2" crossorigin>')
    font_cdn = font_cdn_html(cfg) if book.code == "zh" else ""

    def page(title: str, body: str, *, slug: str, desc: str = "", cls: str = "") -> str:
        fname = "index.html" if slug == "index" else f"{slug}.html"
        og_title = title or full_title
        og_desc = desc or description
        return render(
            layout,
            lang=book.lang,
            edition=book.code,
            title=f"{title} · {full_title}" if title else full_title,
            book_title=esc(full_title),
            short_title=esc(meta["title"]),
            subtitle=esc(meta["subtitle"]),
            description=esc(desc or description),
            og_title=esc(og_title),
            og_description=esc(og_desc),
            og_url=f"{site_url}/{book.code}/{fname}",
            og_image=og_image,
            og_type="article" if cls == "chapter" else "website",
            og_locale=og_locale,
            og_locale_alt=og_locale_alt,
            font_preload=font_preload,
            font_cdn=font_cdn,
            nav=nav_html(book, slug),
            body=body,
            body_class=f"page-{cls}" if cls else "page-chapter",
            asset_prefix="../",
            asset_version=asset_version,
            contents_label=ui["contents"],
            cover_toc=ui["cover_toc"],
            skip=ui["skip"],
            menu_open=ui["menu_open"],
            menu_close=ui["menu_close"],
            theme=ui["theme"],
            author=f"{author_html} · " if author else "",
            year=str(datetime.now().year),
            license=esc(license_name),
            license_url=license_url,
            repo_url=repo_url,
            github_label=ui["github"],
            lang_switch_href=f"../{other}/index.html",
            lang_switch=ui["lang_switch"],
            resume_label=ui["resume"],
        )

    pages: dict[str, str] = {}
    first = book.flow[0] if book.flow else None
    first_href = getattr(first, "page", "index.html") if first else "index.html"
    author_line = f'<p class="hero-author">{author_html}</p>' if author else ""
    home = f"""<article class="home">
  <section class="hero">
    <div class="hero-inner">
      <p class="hero-kicker">{ui["hero_kicker"]}</p>
      <h1 class="hero-title">{esc(meta["title"])}</h1>
      <p class="hero-subtitle">{esc(meta["subtitle"])}</p>
      {author_line}
      <p class="hero-desc">{esc(description)}</p>
      <div class="hero-actions">
        <a class="btn btn-primary" href="{first_href}">{ui["start"]}</a>
        <a class="btn" href="#catalog">{ui["contents"]}</a>
      </div>
      <p class="hero-meta">{esc(book.stats())}</p>
      <p class="hero-license"><a href="{license_url}">{esc(license_name)}</a> · {esc(meta.get("license_note", ""))}</p>
      <a class="resume" id="resume" href="#" hidden><span class="resume-label">{ui["resume"]}</span><span class="resume-title" id="resume-title"></span></a>
    </div>
  </section>
  <section class="catalog" id="catalog">
    <h2 class="section-title">{ui["contents"]}</h2>
    {catalog_html(book)}
  </section>
</article>"""
    pages["index.html"] = page("", home, slug="index", cls="home")

    for item in book.flow:
        if isinstance(item, Part):
            body = part_page_html(item) + pager_html(book, item.slug)
            pages[item.page] = page(item.name or item.label, body, slug=item.slug, cls="part")
        else:
            body = chapter_page_html(item, book, site_url) + pager_html(book, item.slug)
            pages[item.page] = page(item.full_title, body, slug=item.slug,
                                   desc=chapter_description(item), cls="chapter")
    return pages


def build_landing(books: list[Book], cfg: dict, fonts: dict, asset_version: str = "") -> str:
    template = (ROOT / "templates" / "landing.html").read_text(encoding="utf-8")
    site = cfg["site"]["url"].rstrip("/")
    prompts = {
        "zh": f"帮我解读这本 [《走出二选一：大众辩证思维手册》]({site}/zh/dialectics.md)。使用结构化的分析方法。",
        "en": (f"Help me interpret [Beyond Either/Or: A Practical Handbook of Dialectical Thinking]"
               f"({site}/en/dialectics.md). Use a structured analytical approach."),
    }
    ai_labels = {
        "zh": ("✦ AI 帮我读", "复制提示词 · 在 AI 对话中粘贴",
               "提示词已复制，去任意 AI 对话粘贴即可", "复制失败，请手动选择提示词复制"),
        "en": ("✦ Read with AI", "Copies a prompt · paste it into any AI chat",
               "Prompt copied. Paste it into any AI chat.", "Copy failed — please copy the prompt manually."),
    }
    blocks = {}
    for book in books:
        meta = book.meta
        ui = book.ui
        ai_label, ai_hint, ai_toast, ai_fail = ai_labels[book.code]
        blocks[book.code] = f"""<section class="edition" data-lang-block="{book.code}" lang="{book.lang}">
  <p class="edition-kicker">{ui["hero_kicker"]}</p>
  <h1 class="edition-title">{esc(meta["title"])}</h1>
  <p class="edition-subtitle">{esc(meta["subtitle"])}</p>
  <p class="edition-author"><a href="{meta["homepage"]}">{esc(meta["author"])}</a></p>
  <p class="edition-desc">{esc(meta["description"])}</p>
  <p class="edition-stats">{esc(book.stats())}</p>
  <div class="edition-actions">
    <a class="btn btn-primary" href="{book.code}/index.html">{ui["start"]}</a>
    <a class="btn" href="{book.code}/dialectics.pdf">{ui["pdf"]}</a>
    <a class="btn" href="{book.code}/dialectics.epub">{ui["epub"]}</a>
  </div>
  <div class="ai-read">
    <button class="btn btn-ai" data-ai-copy data-prompt="{esc(prompts[book.code])}"
            data-toast="{esc(ai_toast)}" data-fail="{esc(ai_fail)}">{ai_label}</button>
    <span class="ai-status" role="status" aria-live="polite" hidden></span>
    <span class="ai-hint">{ai_hint}</span>
  </div>
</section>"""
    return render(
        template,
        assets="assets",
        asset_version=asset_version,
        font_cdn=font_cdn_html(cfg),
        site_url=site,
        og_description="《走出二选一：大众辩证思维手册》与英文版 Beyond Either/Or 的双语入口。",
        zh_block=blocks.get("zh", ""),
        en_block=blocks.get("en", ""),
        author=esc(cfg["editions"][cfg["site"]["default"]]["author"]),
        license=esc(cfg["editions"][cfg["site"]["default"]]["license"]),
        license_url="https://creativecommons.org/licenses/by-nc-sa/4.0/",
        year=str(datetime.now().year),
    )


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #

def print_cover(meta: dict, ui: dict) -> str:
    author = meta.get("author", "").strip()
    author_html = f'<p class="cover-author">{esc(author)}</p>' if author else ""
    return f"""<section class="pdf-cover" id="cover">
  <div class="cover-frame">
    <p class="cover-kicker">{esc(ui["cover_kicker"])}</p>
    <h1 class="cover-title">{esc(meta["title"])}</h1>
    <div class="cover-rule"></div>
    <p class="cover-subtitle">{esc(meta["subtitle"])}</p>
    {author_html}
    <div class="cover-seal" aria-hidden="true"><span>辩</span><span>证</span></div>
    <p class="cover-foot">{esc(ui["cover_foot"])}</p>
  </div>
</section>"""


def print_colophon(meta: dict, cfg: dict, ui: dict) -> str:
    author = meta.get("author", "").strip()
    today = datetime.now()
    labels = ui["colophon_labels"]
    rows = [(labels["title"], esc(meta["full_title"]))]
    if author:
        rows.append((labels["author"], f'{esc(author)} · <a href="{meta.get("homepage", "")}">{esc(meta.get("homepage", ""))}</a>'))
    rows += [
        (labels["edition"], f"{today.year}-{today.month:02d}"),
        (labels["online"], f'<a href="{esc(cfg["site"].get("url", ""))}">{esc(cfg["site"].get("url", ""))}</a>'),
        (labels["source"], f'<a href="{esc(meta.get("repo", ""))}">{esc(meta.get("repo", ""))}</a>'),
        (labels["license"], f'<a href="{esc(meta.get("license_url", ""))}">{esc(meta.get("license", ""))}</a>'
                            + (f"（{esc(meta.get('license_note', ''))}）" if meta.get("license_note") else "")),
        (labels["typeset"], ui["typeset"]),
        (labels["typeface"], ui.get("typeface", "Noto Serif SC")),
    ]
    dl = "".join(f"<dt>{label}</dt><dd>{value}</dd>" for label, value in rows)
    note = ui["colophon_note"].format(title=esc(meta["full_title"]))
    return f"""<section class="pdf-colophon" id="colophon">
  <h2>{ui["colophon"]}</h2>
  <p>{esc(meta["description"])}</p>
  <dl>{dl}</dl>
  <p class="colophon-note">{note}</p>
</section>"""


def print_toc(book: Book) -> str:
    def row(ch: Chapter, extra: str = "") -> str:
        star = '<span class="toc-star">★</span>' if ch.starred else ""
        sub = f'<span class="toc-sub">{esc(ch.subtitle)}</span>' if ch.subtitle else ""
        return (f'<a class="toc-row{extra}" href="#{ch.slug}">'
                f'<span class="toc-label">{esc(ch.label)}</span>'
                f'<span class="toc-name">{esc(title_text(ch.name or ch.title))}{sub}</span>{star}</a>')

    rows = [row(ch, " toc-solo") for ch in book.loose]
    for part in book.parts:
        rows.append(
            f'<a class="toc-part-head" href="#{part.slug}">'
            f'<span class="toc-label">{esc(part.label)}</span>'
            f'<span class="toc-name">{esc(part.name)}</span></a>'
        )
        rows.extend(row(ch) for ch in part.chapters)
    return f'<section class="pdf-toc" id="toc"><h1>{book.ui["toc"]}</h1>{"".join(rows)}</section>'


def outline_entries(book: Book) -> list[tuple[str, str, str | None]]:
    entries: list[tuple[str, str, str | None]] = [
        ("cover", book.ui["cover"], None),
        ("toc", book.ui["toc"], None),
    ]

    def add(ch: Chapter, parent: str | None) -> None:
        label = f"★ {ch.full_title}" if ch.starred else ch.full_title
        entries.append((ch.slug, label, parent))
        for index, (_anchor, title) in enumerate(ch.sections):
            entries.append((f"{ch.slug}-s{index}", title, ch.slug))

    for ch in book.loose:
        add(ch, None)
    for part in book.parts:
        entries.append((part.slug, f"{part.label} {part.name}".strip(), None))
        for ch in part.chapters:
            add(ch, part.slug)
    return entries


def load_pdf_toc():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import pdf_toc  # noqa: PLC0415
    except ImportError:
        return None
    return pdf_toc if pdf_toc.available() else None


def print_chapter(ch: Chapter) -> str:
    kicker = f'<p class="kicker">{esc(ch.kicker)}</p>' if ch.kicker else ""
    star = '<span class="star">★</span> ' if ch.starred else ""
    sub = f'<p class="chapter-subtitle">{esc(ch.subtitle)}</p>' if ch.subtitle else ""
    return (f'<section class="pdf-chapter" id="{ch.slug}">{kicker}'
            f'<header class="chapter-head"><h1 class="chapter-title">{star}{esc(ch.title)}</h1>'
            f'{sub}</header>'
            f'<div class="prose">{ch.body}</div></section>')


def print_part(part: Part) -> str:
    intro = (f'<div class="prose">{part.intro}</div>' if part.intro
             else '<div class="prose part-intro-empty" aria-hidden="true"></div>')
    items = []
    for n, ch in enumerate(part.chapters, 1):
        sub = f'<span class="part-ch-sub">{esc(ch.subtitle)}</span>' if ch.subtitle else ""
        items.append(
            f'<li><span class="part-ch-num">{n:02d}</span>'
            f'<span class="part-ch-title">{esc(ch.name or ch.title)}{sub}</span></li>'
        )
    listing = f'<ol class="part-chapters">{"".join(items)}</ol>' if items else ""
    if part.name:
        head = (f'<p class="part-label">{esc(part.label)}</p>'
                f'<h1 class="part-title">{esc(part.name)}</h1>')
    else:
        head = f'<h1 class="part-title">{esc(part.label)}</h1>'
    return (f'<section class="pdf-part" id="{part.slug}">'
            f'{head}{intro}{listing}</section>')


def build_print(book: Book, cfg: dict, fonts: dict[int, Path]) -> Path:
    template = (ROOT / "templates" / "print.html").read_text(encoding="utf-8")
    meta = book.meta
    ui = book.ui
    css = "\n".join(
        (ASSETS / "css" / name).read_text(encoding="utf-8")
        for name in ("base.css", "print.css")
    )
    css = (css.replace("__BOOK_TITLE__", meta["title"])
              .replace("__BOOK_SUBTITLE__", meta["subtitle"]))
    if any(fonts.get(k) for k in ("noto", "newsreader")):
        (BUILD / "fonts").mkdir(parents=True, exist_ok=True)
        for name in ("newsreader-400.woff2", "newsreader-700.woff2",
                     "newsreader-400-italic.woff2"):
            src_font = ASSETS / "fonts" / name
            if src_font.is_file():
                shutil.copyfile(src_font, BUILD / "fonts" / name)
        css = css.replace(
            'url("../fonts/',
            f'url("file://{(BUILD / "fonts").resolve()}/',
        )
    else:
        css = re.sub(r"@font-face\s*\{[^}]*\}", "", css)

    sections: list[str] = [print_cover(meta, ui), print_colophon(meta, cfg, ui), print_toc(book)]
    sections.extend(print_chapter(ch) for ch in book.loose)
    for part in book.parts:
        sections.append(print_part(part))
        sections.extend(print_chapter(ch) for ch in part.chapters)

    html_doc = render(
        template,
        lang=book.lang,
        title=esc(meta["full_title"]),
        author=esc(meta.get("author", "")),
        description=esc(meta["description"]),
        keywords=esc(meta.get("keywords", "")),
        subject=esc(meta["subtitle"]),
        css=css,
        content="\n".join(sections),
    )
    BUILD.mkdir(exist_ok=True)
    out = BUILD / f"print-{book.code}.html"
    out.write_text(html_doc, encoding="utf-8")
    return out


def find_chrome() -> str | None:
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    for path in candidates:
        if Path(path).is_file():
            return path
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                 "microsoft-edge", "chrome"):
        if exe := shutil.which(name):
            return exe
    return None


def build_cover_image(meta: dict, ui: dict, out: Path,
                      fonts: dict | None = None) -> Path | None:
    chrome = find_chrome()
    if not chrome:
        return None

    noto = ASSETS / "fonts" / "noto-serif-sc-400.woff2"
    news = ASSETS / "fonts" / "newsreader-400.woff2"
    faces = []
    if noto.exists():
        faces.append(f'@font-face{{font-family:"Noto Serif SC";'
                     f'src:url("file://{noto.resolve()}") format("woff2");font-weight:400}}')
    if news.exists():
        faces.append(f'@font-face{{font-family:"Newsreader";'
                     f'src:url("file://{news.resolve()}") format("woff2");font-weight:400}}')
    font_face = "\n".join(faces)
    family = ('"Newsreader","Noto Serif SC",serif' if meta.get("language", "").startswith("en")
              else '"Noto Serif SC","Songti SC",serif')
    author = meta.get("author", "").strip()
    author_html = f'<p class="author">{esc(author)}</p>' if author else ""
    document = f"""<!doctype html><html lang="{meta['language']}"><head><meta charset="utf-8"><style>
{font_face}
html,body{{margin:0;width:1200px;height:1800px;background:#f0e7d8;
  font-family:{family};color:#241f18}}
.frame{{position:absolute;inset:72px;border:1px solid rgba(156,59,36,.32);
  display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}}
.kicker{{font-size:26px;letter-spacing:.3em;text-indent:.3em;color:#9c3b24;margin:0 0 56px}}
h1{{font-size:{'96px' if len(meta['title']) > 14 else '106px'};letter-spacing:.04em;margin:0;line-height:1.18}}
.rule{{width:66px;height:4px;background:#9c3b24;margin:36px 0 30px}}
.sub{{font-size:34px;letter-spacing:.08em;color:#5d5346;margin:0;max-width:860px;line-height:1.4}}
.author{{font-size:26px;letter-spacing:.2em;color:#8c8477;margin:28px 0 0}}
.seal{{width:152px;height:152px;border-radius:4px;background:#9c3b24;color:#f7efe2;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  font-size:34px;line-height:1.1;margin-top:74px}}
.foot{{position:absolute;left:0;right:0;bottom:58px;font-size:24px;
  letter-spacing:.14em;color:#8c8477;margin:0}}
</style></head><body><div class="frame">
  <p class="kicker">{esc(ui["cover_kicker"])}</p>
  <h1>{esc(meta["title"])}</h1>
  <div class="rule"></div>
  <p class="sub">{esc(meta["subtitle"])}</p>
  {author_html}
  <div class="seal"><span>辩</span><span>证</span></div>
  <p class="foot">{esc(ui["cover_foot"])}</p>
</div></body></html>"""

    BUILD.mkdir(exist_ok=True)
    page = BUILD / f"cover-{meta['code']}.html"
    page.write_text(document, encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="cover-profile-") as profile:
        subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
             "--allow-file-access-from-files",
             "--force-device-scale-factor=1", "--window-size=1200,1800",
             f"--user-data-dir={profile}",
             f"--screenshot={out.resolve()}", page.resolve().as_uri()],
            capture_output=True, text=True,
        )
    return out if out.is_file() and out.stat().st_size > 10_000 else None


def build_share_card(title: str, subtitle: str, kicker: str, lang: str,
                     out: Path, *, bilingual: bool = False) -> bool:
    """生成 800×800 的分享缩略图（微信聊天 / 朋友圈卡片）。"""
    chrome = find_chrome()
    if not chrome:
        return False

    noto = BUILD / "fonts" / "noto-serif-sc-400.woff2"
    news = ASSETS / "fonts" / "newsreader-400.woff2"
    faces = []
    if noto.is_file():
        faces.append(f'@font-face{{font-family:"Noto Serif SC";'
                     f'src:url("file://{noto.resolve()}") format("woff2");font-weight:400}}')
    if news.is_file():
        faces.append(f'@font-face{{font-family:"Newsreader";'
                     f'src:url("file://{news.resolve()}") format("woff2");font-weight:400}}')
    face_css = "\n".join(faces)

    if bilingual:
        title_html = ('<span class="zh">走出二选一</span>'
                      '<span class="en">Beyond Either/Or</span>')
        title_size = "48px"
    else:
        title_html = esc(title)
        title_size = "62px" if lang.startswith("zh") else "44px"

    document = f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><style>
{face_css}
html,body{{margin:0;width:800px;height:800px;background:#f0e7d8;
  font-family:"Newsreader","Noto Serif SC","Songti SC",serif;color:#241f18}}
.card{{position:absolute;inset:34px;border:1px solid rgba(156,59,36,.32);
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  text-align:center;padding:40px 44px}}
.kicker{{margin:0 0 26px;font-size:13px;letter-spacing:.32em;text-indent:.32em;color:#9c3b24}}
h1{{margin:0;font-size:{title_size};line-height:1.22;letter-spacing:.04em}}
h1 .zh,h1 .en{{display:block}}
h1 .en{{font-size:40px;margin-top:10px;letter-spacing:.02em}}
.rule{{width:46px;height:3px;background:#9c3b24;margin:22px 0 18px}}
.sub{{margin:0;font-size:20px;line-height:1.5;color:#5d5346;letter-spacing:.06em;max-width:620px}}
.author{{margin:16px 0 0;font-size:15px;letter-spacing:.16em;color:#8c8477}}
.seal{{margin-top:26px;width:58px;height:58px;border-radius:3px;background:#9c3b24;
  color:#f7efe2;display:flex;flex-direction:column;align-items:center;justify-content:center;
  font-size:18px;line-height:1.08}}
.foot{{position:absolute;left:0;right:0;bottom:22px;margin:0;
  font-size:12px;letter-spacing:.14em;color:#8c8477}}
</style></head><body><div class="card">
  <p class="kicker">{esc(kicker)}</p>
  <h1>{title_html}</h1>
  <div class="rule"></div>
  <p class="sub">{esc(subtitle)}</p>
  <p class="author">Kimmy</p>
  <div class="seal"><span>辩</span><span>证</span></div>
  <p class="foot">dialectics.kimleo.net</p>
</div></body></html>"""

    out.parent.mkdir(parents=True, exist_ok=True)
    page = BUILD / f"share-{out.stem}.html"
    page.write_text(document, encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="share-profile-") as profile:
        subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
             "--allow-file-access-from-files", "--force-device-scale-factor=1",
             "--window-size=800,800", f"--user-data-dir={profile}",
             f"--screenshot={out.resolve()}", page.resolve().as_uri()],
            capture_output=True, text=True,
        )
    return out.is_file() and out.stat().st_size > 5_000


def build_share_cards(books: list[Book]) -> None:
    out_dir = ASSETS / "share"
    for book in books:
        meta = book.meta
        ok = build_share_card(
            meta["title"], meta["subtitle"], book.ui["hero_kicker"],
            book.lang, out_dir / f"{book.code}.png",
        )
        if ok:
            log(f"分享卡片：docs/assets/share/{book.code}.png")
    build_share_card(
        "走出二选一", "A Practical Handbook of Dialectical Thinking",
        "辩证思维手册 · A Practical Handbook", "zh",
        out_dir / "index.png", bilingual=True,
    )


def epub_markdown(source: Path, ui: dict, lang: str) -> tuple[str, set[str]]:
    sys.path.insert(0, str(ROOT / "scripts"))
    import latex_text  # noqa: PLC0415

    text = source.read_text(encoding="utf-8")
    text = re.sub(r"<br\s*/?>", "<br />", text, flags=re.I)
    tag = f'[{ui["deep_dive"]}]'
    text = re.sub(
        r"^(#{2,6}\s+)" + re.escape(tag),
        lambda m: f'{m.group(1)}<span class="tag-advanced">{ui["deep_dive"]}</span>',
        text, flags=re.M,
    )
    text = re.sub(
        r"^(##\s+)(.*?)[（(]([^（）()]*)[）)]\s*$",
        lambda m: f'{m.group(1)}{m.group(2)}\n\n<p class="chapter-sub">{m.group(3)}</p>',
        text, flags=re.M,
    )

    lines, styled, inside = [], [], False
    marker = ui["guide_marker"]
    for line in text.split("\n"):
        if line.startswith("### ") and marker in line:
            inside = True
        elif inside and (line.startswith("### ") or line.startswith("## ")
                         or line.startswith("# ") or line.strip() == "---"):
            inside = False
        match = re.match(r"^(\s*)\* \*\*(.+?)\*\* (\S.*)$", line) if inside else None
        if match:
            styled.append(
                f'{match.group(1)}* **{match.group(2)}**<br />'
                f'<span class="guide-desc">{match.group(3)}</span>'
            )
            continue
        styled.append(line)
    text = "\n".join(styled)

    unknown: set[str] = set()
    # 跳过 \$ 转义的货币：只把未转义的 $...$ 当作公式
    pattern = re.compile(r"(`[^`\n]*`)|(\$\$[^$\n]+\$\$)|((?<!\\)\$[^$\n]+(?<!\\)\$)")

    def repl(match: re.Match[str]) -> str:
        if match.group(1):
            return match.group(1)
        if match.group(2):
            return latex_text.to_html(match.group(2)[2:-2], display=True, report=unknown)
        return latex_text.to_html(match.group(3)[1:-1], report=unknown)

    text = pattern.sub(repl, text)
    return text, unknown


def build_epub(book: Book, cfg: dict, pandoc: str, cover: Path | None, target: Path) -> None:
    meta = book.meta
    source = Path(meta["_path"])
    BUILD.mkdir(exist_ok=True)
    text, unknown = epub_markdown(source, book.ui, book.lang)
    if unknown:
        log(f"提示：EPUB 里有未识别的 LaTeX 命令：{'、'.join(sorted(unknown))}")
    staging = BUILD / f"epub-{book.code}.md"
    staging.write_text(text, encoding="utf-8")

    cmd = [
        pandoc,
        "--from=markdown+smart+lists_without_preceding_blankline",
        "--to=epub3",
        "--toc", "--toc-depth=3", "--split-level=2",
        "--metadata", f"title={meta['full_title']}",
        "--metadata", f"author={meta['author']}",
        "--metadata", f"lang={meta['language']}",
        "--metadata", f"description={meta['description']}",
        "--metadata", f"rights={meta['license']} — {meta['license_note']}",
        "--metadata", f"date={datetime.now():%Y-%m}",
        "--metadata", f"source={cfg['site'].get('url', '')}/{book.code}/",
        "--css", str(ASSETS / "css" / "epub.css"),
    ]
    if cover:
        cmd += ["--epub-cover-image", str(cover)]
    for name in ("newsreader-400.woff2", "newsreader-700.woff2", "newsreader-400-italic.woff2"):
        font = ASSETS / "fonts" / name
        if font.is_file():
            cmd += ["--epub-embed-font", str(font)]
    cmd += ["--output", str(target), str(staging)]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not target.is_file():
        die(f"EPUB 生成失败：{proc.stderr.strip()[:400]}")


def build_pdf(print_html: Path, target: Path) -> None:
    chrome = find_chrome()
    if not chrome:
        die("找不到 Chrome/Chromium/Edge，无法打印 PDF。")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cdp-profile-") as profile:
        cmd = [
            chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
            "--allow-file-access-from-files", "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=15000", f"--user-data-dir={profile}",
            f"--print-to-pdf={target.resolve()}", print_html.resolve().as_uri(),
        ]
        if sys.platform.startswith("linux"):
            cmd.insert(1, "--no-sandbox")
            cmd.insert(2, "--disable-dev-shm-usage")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if not target.is_file():
            die(f"PDF 生成失败：{(proc.stderr or proc.stdout).strip()[:500]}")


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #

def load_config() -> dict:
    with (ROOT / "book.toml").open("rb") as fh:
        return tomllib.load(fh)


def prepare_fonts(cfg: dict, html_text: str) -> dict[int, Path]:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from prepare_fonts import ensure_fonts  # noqa: PLC0415
    except ImportError:
        return {}
    return ensure_fonts(
        set(html_text),
        out_dir=BUILD / "fonts",
        cache_dir=ROOT / ".cache" / "fonts",
        explicit=cfg["fonts"].get("source") or None,
    )


def prepare_newsreader(cfg: dict, english_text: str) -> dict:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from prepare_fonts import ensure_newsreader  # noqa: PLC0415
    except ImportError:
        return {}
    chars = {c for c in english_text if ord(c) <= 0x2E7F}
    return ensure_newsreader(
        chars,
        out_dir=ASSETS / "fonts",
        cache_dir=ROOT / ".cache" / "fonts",
        explicit=cfg["fonts"].get("newsreader_source") or None,
    )


def clean_outputs(cfg: dict) -> int:
    removed = 0
    for code in cfg["editions"]:
        folder = SITE / code
        if not folder.is_dir():
            continue
        for old in folder.glob("*.html"):
            old.unlink()
            removed += 1
        for name in ("dialectics.pdf", "dialectics.epub", "dialectics.md"):
            path = folder / name
            if path.exists():
                path.unlink()
                removed += 1
    landing = SITE / "index.html"
    if landing.exists():
        landing.unlink()
        removed += 1
    shutil.rmtree(BUILD, ignore_errors=True)
    shutil.rmtree(ROOT / ".cache", ignore_errors=True)
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-pdf", action="store_true", help="跳过 PDF")
    parser.add_argument("--no-epub", action="store_true", help="跳过 EPUB")
    parser.add_argument("--no-fonts", action="store_true", help="跳过字体子集化")
    parser.add_argument("--clean", action="store_true", help="删除生成页面与缓存")
    args = parser.parse_args()

    started = time.time()
    cfg = load_config()
    if args.clean:
        removed = clean_outputs(cfg)
        print(f"已删除 {removed} 个生成文件（源文件与 assets 保留）")
        return 0

    pandoc = find_pandoc()
    books: list[Book] = []
    step("解析 Markdown")
    for code, meta in cfg["editions"].items():
        meta = dict(meta)
        meta["code"] = code
        source = ROOT / meta["source"]
        if not source.is_file():
            die(f"源文件不存在：{source}")
        book = parse_book(source, code, meta["language"])
        book.meta.update(meta)
        book.meta["_path"] = str(source)
        books.append(book)
        log(f"[{code}] 《{book.title}》 {book.stats()}")

    step("pandoc 渲染章节")
    for book in books:
        for part in book.parts:
            part.intro = pandoc_md_to_html(pandoc, part.intro_md)
        for chapter in book.chapters:
            body = pandoc_md_to_html(pandoc, chapter.body_md)
            chapter.body = style_guide_section(body, book.ui["guide_marker"])
            chapter.sections = extract_sections(chapter.body)

    step("生成网页")
    # 只用 CSS/JS/字体等代码资源的 mtime 做缓存版本；分享图重生成不改动版本号。
    asset_version = str(int(max(
        p.stat().st_mtime for p in ASSETS.rglob("*")
        if p.is_file() and "share" not in p.relative_to(ASSETS).parts
    )))
    pages = {book.code: build_site(book, cfg, {}, asset_version) for book in books}
    landing = build_landing(books, cfg, {}, asset_version)
    site_text = landing + "\n" + "\n".join("\n".join(p.values()) for p in pages.values())
    BUILD.mkdir(exist_ok=True)
    (BUILD / "chars.txt").write_text(
        "".join(sorted(set(re.sub(r"<[^>]+>", "", html.unescape(site_text))))),
        encoding="utf-8",
    )

    english_text = landing + "\n" + "\n".join(pages["en"].values())

    fonts: dict = {"noto": {}, "newsreader": {}}
    if not args.no_fonts:
        fonts["noto"] = prepare_fonts(cfg, site_text)
        fonts["newsreader"] = prepare_newsreader(cfg, english_text)
    else:
        for weight in (400, 700):
            candidate = BUILD / "fonts" / f"noto-serif-sc-{weight}.woff2"
            if candidate.is_file():
                fonts["noto"][weight] = candidate
        for key, name in ((400, "normal"), (700, "normal"), (400, "italic")):
            candidate = ASSETS / "fonts" / f"newsreader-{key}" + ("-italic" if name == "italic" else "") + ".woff2"
            if candidate.is_file():
                fonts["newsreader"][(key, name)] = candidate
    if not fonts:
        log("提示：没有可用字体文件，网页与 PDF 会回退到系统衬线字体")

    build_share_cards(books)
    pages = {book.code: build_site(book, cfg, fonts, asset_version) for book in books}
    landing = build_landing(books, cfg, fonts, asset_version)

    for book in books:
        folder = SITE / book.code
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob("*.html"):
            old.unlink()
        for name, content in pages[book.code].items():
            (folder / name).write_text(content, encoding="utf-8")
    for old in SITE.glob("*.html"):
        old.unlink()
    for legacy in ("dialectics.pdf", "dialectics.epub"):
        (SITE / legacy).unlink(missing_ok=True)
    (SITE / "index.html").write_text(landing, encoding="utf-8")

    # AI 可直接抓取的 Markdown 原文
    for code, name in (("zh", "dialectics.md"), ("en", "dialectics_en.md")):
        src = MARKDOWN / name
        if src.is_file():
            shutil.copyfile(src, SITE / code / "dialectics.md")
    log(f"docs/ 共 {sum(len(p) for p in pages.values()) + 1} 个页面")

    toc_tool = load_pdf_toc()
    for book in books:
        folder = SITE / book.code
        if not args.no_pdf:
            step(f"排版 PDF（{book.code}）")
            print_html = build_print(book, cfg, fonts)
            target = folder / "dialectics.pdf"
            build_pdf(print_html, target)
            entries = outline_entries(book)
            if toc_tool:
                found = toc_tool.locate_pages(target, entries, header=book.meta["title"])
                if found and toc_tool.add_outline(
                    target, entries, found,
                    title=book.meta["full_title"],
                    author=book.meta.get("author", ""),
                ):
                    log(f"已写入 {len(found)} 条 PDF 书签")
            log(f"docs/{book.code}/dialectics.pdf（{target.stat().st_size / 1024 / 1024:.1f} MB）")

        if not args.no_epub:
            step(f"打包 EPUB（{book.code}）")
            cover = build_cover_image(book.meta, book.ui, BUILD / f"cover-{book.code}.png", fonts)
            epub_path = folder / "dialectics.epub"
            build_epub(book, cfg, pandoc, cover, epub_path)
            log(f"docs/{book.code}/dialectics.epub（{epub_path.stat().st_size / 1024 / 1024:.1f} MB）")

    print(f"\n\033[32m完成\033[0m，用时 {time.time() - started:.1f}s")
    print("  Web  docs/index.html → docs/zh/ · docs/en/")
    if not args.no_pdf:
        print("  PDF  docs/{zh,en}/dialectics.pdf")
    if not args.no_epub:
        print("  EPUB docs/{zh,en}/dialectics.epub")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
