#!/usr/bin/env python3
"""《走出二选一》发布框架。

一条命令把产物写进 docs/：
  * docs/*.html —— 可分章阅读的静态站点（GitHub Pages 直接指向 /docs）
  * docs/dialectics.pdf —— A4 排版的 PDF（Chromium 打印引擎 + pypdf 书签）

用法：
  python3 build.py            # 全量构建
  python3 build.py --no-pdf   # 只构建网页
  python3 build.py --no-fonts # 跳过字体子集化
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
# 站点直接生成在 docs/ 下：源文件、样式、字体与页面同目录，
# 提交后把 GitHub Pages 设为分支 master 的 /docs 即可，无需在云端构建。
SITE = ROOT / "docs"
ASSETS = SITE / "assets"
BUILD = ROOT / "build"

CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
          "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12}


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
    """把一段 Markdown 渲染为 HTML 片段。数学公式输出 MathML，网页与 PDF 通吃。"""
    if not markdown.strip():
        return ""
    proc = subprocess.run(
        [exe, "--from=markdown+smart+lists_without_preceding_blankline",
         "--to=html5", "--mathml",
         "--wrap=none", "--no-highlight"],
        input=markdown, capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        die(f"pandoc 渲染失败：{proc.stderr.strip()}")
    return tidy(proc.stdout.strip())


def tidy(fragment: str) -> str:
    """收拾 pandoc 输出：去掉标题前后的分隔线，给宽表格加滚动容器。"""
    # 标题里的 [进阶深潜] 是分级标签，渲染成小徽标；正文里用反引号说明的
    # `[进阶深潜]` 保持原样，避免把代码样式包进徽标里
    def _tag(match: re.Match[str]) -> str:
        inner = match.group(2).replace(
            "[进阶深潜]", '<span class="tag-advanced">进阶深潜</span>'
        )
        inner = re.sub(r"^★\s*", '<span class="star">★</span> ', inner)
        return match.group(1) + inner + match.group(3)

    fragment = re.sub(
        r"(<h[1-6][^>]*>)(.*?)(</h[1-6]>)", _tag, fragment, flags=re.S
    )
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


def plain_text(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def render(template: str, **values: str) -> str:
    def sub(match: re.Match[str]) -> str:
        key = match.group(1)
        return values.get(key, "")
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
    sections: list[tuple[str, str]] = field(default_factory=list)  # (锚点, 三级标题)

    @property
    def full_title(self) -> str:
        return f"{self.title}（{self.subtitle}）" if self.subtitle else self.title

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


@dataclass
class Book:
    title: str
    meta: dict
    parts: list[Part]
    loose: list[Chapter]

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
        numbered = sum(1 for p in self.parts if p.label.startswith("第"))
        chaps = sum(1 for c in self.chapters if c.title.startswith("第"))
        chars = len(re.findall(r"[\u4e00-\u9fff]", self.meta["source_text"]))
        return f"{numbered} 个部分 · {chaps} 章 · 约 {chars / 10000:.0f} 万字"


def split_subtitle(title: str) -> tuple[str, str]:
    """把标题末尾的「（如何……）」拆成副标题。"""
    match = re.match(r"^(.*?)（([^（）]*)）\s*$", title.strip())
    if match and len(match.group(1)) > 4:
        return match.group(1).strip(), match.group(2).strip()
    return title.strip(), ""


def split_label(title: str) -> tuple[str, str]:
    """把「第 1 章 张力的四种形态」拆成（第 1 章，张力的四种形态）。"""
    if title.strip() in {"附录", "正文", "目录"}:
        return title.strip(), ""
    match = re.match(r"^((?:第\s*\d+\s*章)|(?:第[一二三四五六七八九十]+部分)|"
                     r"(?:附录\s*[A-Za-z])|序章|结语|前言|后记)\s*(.*)$", title)
    if match:
        name = re.sub(r"^[：:、，,\s]+", "", match.group(2).strip())
        return match.group(1).strip(), name
    return "", title


def slugify_chapter(title: str, index: int) -> str:
    if title.startswith("前言"):
        return "preface"
    if title.startswith("序章"):
        return "prologue"
    if title.startswith("结语"):
        return "epilogue"
    if m := re.match(r"^第\s*(\d+)\s*章", title):
        return f"ch{int(m.group(1)):02d}"
    if m := re.match(r"^附录\s*([A-Za-z])", title):
        return f"appendix-{m.group(1).lower()}"
    return f"ch{index:02d}-x"


def slugify_part(title: str, index: int) -> str:
    if m := re.match(r"^第([一二三四五六七八九十]+)部分", title):
        return f"part-{CN_NUM.get(m.group(1), index)}"
    if title.startswith("附录"):
        return "appendix"
    return f"part-{index}"


def parse_book(path: Path) -> Book:
    text = path.read_text(encoding="utf-8")
    stray = re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text)
    if stray:
        log(f"警告：源文件里有 {len(stray)} 个控制字符，可能有 LaTeX 被转义"
            "（例如 \\frac 变成换页符、\\neg 变成换行）。请检查后再发布。")

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
        # 「★」是入门核心章节的标记，不参与标题解析，单独记为星标
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
            title, subtitle = split_subtitle(raw_title)
            label, name = split_label(title)
            chapter = Chapter(
                title=title, subtitle=subtitle, body_md=body,
                slug=slugify_chapter(title, chapter_index),
                label=label, name=name, starred=starred,
            )
            if current is not None:
                chapter.part = current
                current.chapters.append(chapter)
            else:
                loose.append(chapter)

    if not parts and not loose:
        die(f"没有从 {path} 里解析出任何章节标题")

    return Book(title=title, meta={"source_text": text, "path": str(path)},
                parts=parts, loose=loose)


# --------------------------------------------------------------------------- #
# 页面片段
# --------------------------------------------------------------------------- #

def nav_html(book: Book, current: str) -> str:
    rows = [f'<a class="nav-cover{" is-active" if current == "index" else ""}" '
            f'href="index.html">封面与目录</a>']

    def chapter_row(ch: Chapter) -> str:
        active = " is-active" if current == ch.slug else ""
        aria = ' aria-current="page"' if current == ch.slug else ""
        num = ch.label or ""
        star = '<span class="nav-star" title="入门核心必读">★</span>' if ch.starred else ""
        sub = f'<span class="nav-sub">{esc(ch.subtitle)}</span>' if ch.subtitle else ""
        return (f'<li><a class="nav-item{active}" href="{ch.page}"{aria} '
                f'title="{esc(ch.full_title)}">'
                f'<span class="nav-num">{esc(num)}</span>'
                f'<span class="nav-name"><span class="nav-main">{esc(ch.name or ch.title)}</span>'
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

    def card(item, direction: str) -> str:
        if item is None:
            return '<span class="pager-card is-empty"></span>'
        title = getattr(item, "title")
        page = getattr(item, "page")
        return (f'<a class="pager-card pager-{direction}" href="{page}">'
                f'<span class="pager-dir">{"← 上一章" if direction == "prev" else "下一章 →"}</span>'
                f'<span class="pager-title">{esc(title)}</span></a>')

    return (f'<nav class="pager" aria-label="章节导航">{card(prev_item, "prev")}'
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
        star = '<span class="star" title="入门核心必读">★</span>' if ch.starred else ""
        sub = f'<span class="part-ch-sub">{esc(ch.subtitle)}</span>' if ch.subtitle else ""
        items.append(
            f'<li><a href="{ch.page}"><span class="part-ch-num">{n:02d}</span>'
            f'<span class="part-ch-title">{esc(ch.title)}{star}{sub}</span>'
            f'<span class="part-ch-arrow">→</span></a></li>'
        )
    listing = ('<ol class="part-chapters">' + "".join(items) + "</ol>") if items else ""
    return f'<article class="part-page">{head}{intro}{listing}</article>'


def chapter_page_html(ch: Chapter) -> str:
    kicker = f'<p class="kicker">{esc(ch.kicker)}</p>' if ch.kicker else ""
    star = '<span class="star" title="入门核心必读">★</span> ' if ch.starred else ""
    sub = f'<p class="chapter-sub">{esc(ch.subtitle)}</p>' if ch.subtitle else ""
    return (f'<article class="chapter">{kicker}'
            f'<header class="chapter-head"><h1>{star}{esc(ch.title)}</h1>{sub}</header>'
            f'<div class="prose">{ch.body}</div></article>')


def extract_sections(fragment: str) -> list[tuple[str, str]]:
    """取出一章里的三级标题，用于 PDF 书签的第二层。"""
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
        return '<span class="catalog-star" title="入门核心必读">★</span>' if ch.starred else ""

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
# 构建
# --------------------------------------------------------------------------- #

def build_site(book: Book, cfg: dict, pandoc: str, fonts: dict[int, Path]) -> dict[str, str]:
    layout = (ROOT / "templates" / "layout.html").read_text(encoding="utf-8")
    meta = cfg["book"]
    full_title = meta["full_title"]
    description = meta["description"]
    lang = meta["language"]
    pdf_name = cfg["site"]["pdf_name"]
    epub_name = cfg["site"].get("epub_name", "dialectics.epub")
    author = meta.get("author", "").strip()
    license_name = meta.get("license", "")
    license_url = meta.get("license_url", "")
    license_note = meta.get("license_note", "")
    repo_url = meta.get("repo", "")
    site_url = cfg["site"].get("url", "")

    font_preload = ""
    if fonts.get(400):
        font_preload = ('<link rel="preload" href="assets/fonts/noto-serif-sc-400.woff2" '
                        'as="font" type="font/woff2" crossorigin>')

    def page(title: str, body: str, *, slug: str, desc: str = "", cls: str = "") -> str:
        return render(
            layout,
            lang=lang,
            title=f"{title} · {full_title}" if title else full_title,
            book_title=esc(full_title),
            short_title=esc(meta["title"]),
            subtitle=esc(meta["subtitle"]),
            description=esc(desc or description),
            font_preload=font_preload,
            nav=nav_html(book, slug),
            body=body,
            body_class=f"page-{cls}" if cls else "page-chapter",
            pdf_href=pdf_name,
            epub_href=epub_name,
            author=f"{esc(author)} · " if author else "",
            year=str(datetime.now().year),
            license=esc(license_name),
            license_url=license_url,
            license_note=esc(license_note),
            repo_url=repo_url,
            site_url=site_url,
        )

    pages: dict[str, str] = {}

    # 封面 + 目录
    first = book.flow[0] if book.flow else None
    first_href = getattr(first, "page", "index.html") if first else "index.html"
    author_line = f'<p class="hero-author">{esc(author)}</p>' if author else ""
    home = f"""<article class="home">
  <section class="hero">
    <div class="hero-inner">
      <p class="hero-kicker">辩证思维手册</p>
      <h1 class="hero-title">走出二选一</h1>
      <p class="hero-subtitle">{esc(meta["subtitle"])}</p>
      {author_line}
      <p class="hero-desc">{esc(description)}</p>
      <div class="hero-actions">
        <a class="btn btn-primary" href="{first_href}">开始阅读</a>
        <a class="btn" href="#catalog">目录</a>
        <a class="btn btn-ghost" href="{pdf_name}">PDF</a>
        <a class="btn btn-ghost" href="{epub_name}">ePub</a>
      </div>
      <p class="hero-meta">{esc(book.stats())}</p>
      <p class="hero-license"><a href="{license_url}">{esc(license_name)}</a> · {license_note}</p>
      <a class="resume" id="resume" href="#" hidden><span class="resume-label">继续上次阅读</span><span class="resume-title" id="resume-title"></span></a>
    </div>
  </section>
  <section class="catalog" id="catalog">
    <h2 class="section-title">目录</h2>
    {catalog_html(book)}
  </section>
</article>"""
    pages["index.html"] = page("", home, slug="index", cls="home")

    for item in book.flow:
        if isinstance(item, Part):
            body = part_page_html(item) + pager_html(book, item.slug)
            pages[item.page] = page(item.name or item.label, body, slug=item.slug, cls="part")
        else:
            body = chapter_page_html(item) + pager_html(book, item.slug)
            pages[item.page] = page(item.title, body, slug=item.slug,
                                   desc=chapter_description(item), cls="chapter")
    return pages


def print_cover(meta: dict) -> str:
    author = meta.get("author", "").strip()
    author_html = f'<p class="cover-author">{esc(author)}</p>' if author else ""
    return f"""<section class="pdf-cover" id="cover">
  <div class="cover-frame">
    <p class="cover-kicker">辩证思维手册</p>
    <h1 class="cover-title">{esc(meta["title"])}</h1>
    <div class="cover-rule"></div>
    <p class="cover-subtitle">{esc(meta["subtitle"])}</p>
    {author_html}
    <div class="cover-seal" aria-hidden="true"><span>辩</span><span>证</span></div>
    <p class="cover-foot">走出非黑即白 · 看清问题的结构</p>
  </div>
</section>"""


def print_colophon(meta: dict, cfg: dict) -> str:
    author = meta.get("author", "").strip()
    license_name = meta.get("license", "")
    license_note = meta.get("license_note", "")
    today = datetime.now()
    rows = [("书名", esc(meta["full_title"]))]
    if author:
        rows.append(("作者", f'{esc(author)} · <a href="{meta.get("homepage", "")}">{esc(meta.get("homepage", ""))}</a>'))
    rows += [
        ("版本", f"{today.year} 年 {today.month} 月"),
        ("在线版", f'<a href="{esc(cfg["site"].get("url", ""))}">{esc(cfg["site"].get("url", ""))}</a>'),
        ("源码", f'<a href="{esc(meta.get("repo", ""))}">{esc(meta.get("repo", ""))}</a>'),
        ("许可", f'<a href="{esc(meta.get("license_url", ""))}">{esc(license_name)}</a>'
                + (f"（{esc(license_note)}）" if license_note else "")),
        ("排版", "Markdown → pandoc → Chromium 打印引擎"),
        ("字体", "Noto Serif SC"),
    ]
    dl = "".join(f"<dt>{label}</dt><dd>{value}</dd>" for label, value in rows)
    return f"""<section class="pdf-colophon" id="colophon">
  <h2>本书说明</h2>
  <p>{esc(meta["description"])}</p>
  <dl>{dl}</dl>
  <p class="colophon-note">本书为《{esc(meta["full_title"])}》的排版版本，正文内容以 Markdown 源文件为准。</p>
</section>"""


def print_toc(book: Book) -> str:
    def row(ch: Chapter, extra: str = "") -> str:
        star = '<span class="toc-star">★</span>' if ch.starred else ""
        sub = f'<span class="toc-sub">{esc(ch.subtitle)}</span>' if ch.subtitle else ""
        return (f'<a class="toc-row{extra}" href="#{ch.slug}">'
                f'<span class="toc-label">{esc(ch.label)}</span>'
                f'<span class="toc-name">{esc(ch.name or ch.title)}{sub}</span>{star}</a>')

    rows = [row(ch, " toc-solo") for ch in book.loose]
    for part in book.parts:
        rows.append(
            f'<a class="toc-part-head" href="#{part.slug}">'
            f'<span class="toc-label">{esc(part.label)}</span>'
            f'<span class="toc-name">{esc(part.name)}</span></a>'
        )
        rows.extend(row(ch) for ch in part.chapters)
    return f'<section class="pdf-toc" id="toc"><h1>目录</h1>{"".join(rows)}</section>'


def outline_entries(book: Book) -> list[tuple[str, str, str | None]]:
    """PDF 书签的扁平清单：(slug, 标题, 父级 slug)。"""
    entries: list[tuple[str, str, str | None]] = [
        ("cover", "封面", None),
        ("toc", "目录", None),
    ]
    def label(ch: Chapter) -> str:
        title = ch.full_title
        return f"★ {title}" if ch.starred else title

    def add(ch: Chapter, parent: str | None) -> None:
        entries.append((ch.slug, label(ch), parent))
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
    # 没有导言的部分也留一段空白，别让章节列表紧贴标题
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
    meta = cfg["book"]
    css = "\n".join(
        (ASSETS / "css" / name).read_text(encoding="utf-8")
        for name in ("base.css", "print.css")
    )
    css = (css.replace("__BOOK_TITLE__", meta["title"])
              .replace("__BOOK_SUBTITLE__", meta["subtitle"]))
    if fonts:
        css = css.replace(
            'url("../fonts/',
            f'url("file://{(ASSETS / "fonts").resolve()}/',
        )
    else:
        css = re.sub(r"@font-face\s*\{[^}]*\}", "", css)

    # 阅读顺序：封面 → 版权说明 → 目录 → 无归属章节 → 每个部分（部分页 + 各章）
    sections: list[str] = [print_cover(meta), print_colophon(meta, cfg), print_toc(book)]
    sections.extend(print_chapter(ch) for ch in book.loose)
    for part in book.parts:
        sections.append(print_part(part))
        sections.extend(print_chapter(ch) for ch in part.chapters)

    html_doc = render(
        template,
        lang=meta["language"],
        title=esc(cfg["pdf"]["title"]),
        author=esc(meta.get("author", "")),
        description=esc(meta["description"]),
        keywords=esc(cfg["pdf"].get("keywords", "")),
        subject=esc(cfg["pdf"].get("subject", "")),
        css=css,
        content="\n".join(sections),
    )
    BUILD.mkdir(exist_ok=True)
    out = BUILD / "print.html"
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


def build_cover_image(meta: dict, out: Path) -> Path | None:
    """把封面渲染成 1200×1800 的 PNG，供 EPUB 使用。"""
    chrome = find_chrome()
    if not chrome:
        return None

    font = ASSETS / "fonts" / "noto-serif-sc-400.woff2"
    font_face = (
        f'@font-face{{font-family:"Noto Serif SC";'
        f'src:url("file://{font.resolve()}") format("woff2");font-weight:400}}'
        if font.exists() else ""
    )
    author = meta.get("author", "").strip()
    author_html = f'<p class="author">{esc(author)}</p>' if author else ""
    document = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>
{font_face}
html,body{{margin:0;width:1200px;height:1800px;background:#f0e7d8;
  font-family:"Noto Serif SC","Songti SC",serif;color:#241f18}}
.frame{{position:absolute;inset:72px;border:1px solid rgba(156,59,36,.32);
  display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}}
.kicker{{font-size:26px;letter-spacing:.52em;text-indent:.52em;color:#9c3b24;margin:0 0 56px}}
h1{{font-size:106px;letter-spacing:.1em;text-indent:.1em;margin:0;line-height:1.18}}
.rule{{width:66px;height:4px;background:#9c3b24;margin:36px 0 30px}}
.sub{{font-size:38px;letter-spacing:.34em;text-indent:.34em;color:#5d5346;margin:0}}
.author{{font-size:26px;letter-spacing:.2em;color:#8c8477;margin:28px 0 0}}
.seal{{width:152px;height:152px;border-radius:4px;background:#9c3b24;color:#f7efe2;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  font-size:34px;line-height:1.1;margin-top:86px}}
.foot{{position:absolute;left:0;right:0;bottom:58px;font-size:24px;
  letter-spacing:.2em;text-indent:.2em;color:#8c8477;margin:0}}
</style></head><body><div class="frame">
  <p class="kicker">辩证思维手册</p>
  <h1>{esc(meta["title"])}</h1>
  <div class="rule"></div>
  <p class="sub">{esc(meta["subtitle"])}</p>
  {author_html}
  <div class="seal"><span>辩</span><span>证</span></div>
  <p class="foot">走出非黑即白 · 看清问题的结构</p>
</div></body></html>"""

    BUILD.mkdir(exist_ok=True)
    page = BUILD / "cover.html"
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


def build_epub(book: Book, cfg: dict, pandoc: str, cover: Path | None, target: Path) -> None:
    meta = cfg["book"]
    source = ROOT / meta["source"]
    # 源码里保留 [进阶深潜] 字面标签，EPUB 里换成小徽标
    text = source.read_text(encoding="utf-8").replace(
        "[进阶深潜]", '<span class="tag-advanced">进阶深潜</span>'
    )
    # EPUB 是 XHTML，原始 HTML 里的 <br> 必须写成自闭合，否则 Books 会报标签未闭合
    text = re.sub(r"<br\s*/?>", "<br />", text, flags=re.I)
    # 章节标题末尾的「（副标题）」拆成下一行的小字，和网页/PDF 的层次保持一致
    text = re.sub(
        r"^(##\s+)(.*?)（([^（）]*)）\s*$",
        lambda m: f'{m.group(1)}{m.group(2)}\n\n<p class="chapter-sub">{m.group(3)}</p>',
        text, flags=re.M,
    )
    BUILD.mkdir(exist_ok=True)
    staging = BUILD / "epub.md"
    staging.write_text(text, encoding="utf-8")

    cmd = [
        pandoc,
        "--from=markdown+smart+lists_without_preceding_blankline",
        "--to=epub3",
        "--mathml",
        "--toc", "--toc-depth=2", "--split-level=1",
        "--metadata", f"title={meta['full_title']}",
        "--metadata", f"author={meta['author']}",
        "--metadata", f"lang={meta['language']}",
        "--metadata", f"description={meta['description']}",
        "--metadata", f"rights={meta['license']}（{meta['license_note']}）",
        "--metadata", f"date={datetime.now():%Y-%m}",
        "--metadata", f"source={cfg['site'].get('url', '')}",
        "--css", str(ASSETS / "css" / "epub.css"),
    ]
    if cover:
        cmd += ["--epub-cover-image", str(cover)]
    cmd += ["--output", str(target), str(staging)]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not target.is_file():
        die(f"EPUB 生成失败：{proc.stderr.strip()[:400]}")


def build_pdf(print_html: Path, target: Path) -> None:
    chrome = find_chrome()
    if not chrome:
        die("找不到 Chrome/Chromium/Edge，无法打印 PDF。可安装 Chrome 或改用其他 PDF 引擎。")

    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cdp-profile-") as profile:
        cmd = [
            chrome,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--allow-file-access-from-files",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=15000",
            f"--user-data-dir={profile}",
            f"--print-to-pdf={target.resolve()}",
            print_html.resolve().as_uri(),
        ]
        if shutil.which("chromium") or "chromium" in chrome.lower():
            cmd.insert(1, "--no-sandbox")
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
        out_dir=ASSETS / "fonts",
        cache_dir=ROOT / ".cache" / "fonts",
        explicit=cfg["fonts"].get("source") or None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-pdf", action="store_true", help="只构建网页")
    parser.add_argument("--no-epub", action="store_true", help="跳过 EPUB")
    parser.add_argument("--no-fonts", action="store_true", help="跳过字体子集化")
    parser.add_argument("--clean", action="store_true", help="删除生成页面与构建缓存")
    args = parser.parse_args()

    started = time.time()
    cfg = load_config()
    source = ROOT / cfg["book"]["source"]
    if not source.is_file():
        die(f"源文件不存在：{source}")

    if args.clean:
        removed = 0
        for old in SITE.glob("*.html"):
            old.unlink()
            removed += 1
        pdf = SITE / cfg["site"]["pdf_name"]
        if pdf.exists():
            pdf.unlink()
            removed += 1
        shutil.rmtree(BUILD, ignore_errors=True)
        shutil.rmtree(ROOT / ".cache", ignore_errors=True)
        print(f"已删除 {removed} 个生成文件（源文件与 assets 保留）")
        return 0

    pandoc = find_pandoc()

    step("解析 Markdown")
    book = parse_book(source)
    log(f"《{book.title}》 {book.stats()}")

    step("pandoc 渲染章节")
    for part in book.parts:
        part.intro = pandoc_md_to_html(pandoc, part.intro_md)
    for chapter in book.chapters:
        chapter.body = pandoc_md_to_html(pandoc, chapter.body_md)
        chapter.sections = extract_sections(chapter.body)
        if not chapter.body:
            log(f"警告：{chapter.title} 没有正文")

    step("生成网页")
    pages = build_site(book, cfg, pandoc, {})
    site_text = "\n".join(pages.values())
    BUILD.mkdir(exist_ok=True)
    (BUILD / "chars.txt").write_text(
        "".join(sorted(set(re.sub(r"<[^>]+>", "", html.unescape(site_text))))),
        encoding="utf-8",
    )

    fonts: dict[int, Path] = {}
    if not args.no_fonts:
        fonts = prepare_fonts(cfg, site_text)
    else:
        for weight in (400, 700):
            candidate = ASSETS / "fonts" / f"noto-serif-sc-{weight}.woff2"
            if candidate.is_file():
                fonts[weight] = candidate
    if not fonts:
        log("提示：没有可用字体文件，网页与 PDF 会回退到系统自带的宋体/衬线字体")

    # 字体确定后重新生成一次，带上 preload 标签
    pages = build_site(book, cfg, pandoc, fonts)

    SITE.mkdir(exist_ok=True)
    # 只清理上一次生成的页面；docs/dialectics.md 与 docs/assets 是源文件，必须保留
    for old in SITE.glob("*.html"):
        old.unlink()
    for name, content in pages.items():
        (SITE / name).write_text(content, encoding="utf-8")
    log(f"docs/ 共 {len(pages)} 个页面")

    if args.no_pdf:
        log("跳过 PDF")
    else:
        step("排版 PDF")
        pdf_name = cfg["site"]["pdf_name"]
        target = SITE / pdf_name
        entries = outline_entries(book)
        header = cfg["book"]["title"]

        print_html = build_print(book, cfg, fonts)
        build_pdf(print_html, target)

        toc_tool = load_pdf_toc()
        if toc_tool:
            # 阅读器侧边栏的书签：用 Chromium 写入的命名目标定位每章首页
            pages = toc_tool.locate_pages(target, entries, header=header)
            missing = [name for slug, name, _ in entries if slug not in pages]
            if missing:
                log(f"提示：{len(missing)} 个标题未能定位：{'、'.join(missing[:3])}")
            if pages and toc_tool.add_outline(
                target, entries, pages,
                title=cfg["pdf"]["title"],
                author=cfg["book"].get("author", ""),
            ):
                log(f"已写入 {len(pages)} 条 PDF 书签")
        else:
            log("提示：安装 pypdf 可生成 PDF 侧边栏书签（pip install pypdf）")

        size = target.stat().st_size / 1024 / 1024
        log(f"docs/{pdf_name}（{size:.1f} MB）")

    if args.no_epub:
        log("跳过 EPUB")
    else:
        step("打包 EPUB")
        cover = build_cover_image(cfg["book"], BUILD / "cover.png")
        epub_path = SITE / cfg["site"]["epub_name"]
        build_epub(book, cfg, pandoc, cover, epub_path)
        log(f"docs/{cfg['site']['epub_name']}"
            f"（{epub_path.stat().st_size / 1024 / 1024:.1f} MB）")

    print(f"\n\033[32m完成\033[0m，用时 {time.time() - started:.1f}s")
    print(f"  Web  docs/index.html")
    if not args.no_pdf:
        print(f"  PDF  docs/{cfg['site']['pdf_name']}")
    if not args.no_epub:
        print(f"  EPUB docs/{cfg['site']['epub_name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
