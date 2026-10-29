#!/usr/bin/env python3
"""Noto Serif SC 字体准备：查找本地字体 → 实例化静态字重 → 按用字子集化 → woff2。

为什么要实例化（instancer）而不是直接子集化可变字体？
Chromium 的 Skia PDF 后端无法嵌入可变字体，会把每个字形降级成 Type3 路径字体，
一份 150 页的书会因此膨胀到 20 MB 以上。静态字重则正常嵌入为 TrueType 子集。

用法：
    python3 scripts/prepare_fonts.py --chars-file build/chars.txt --out assets/fonts

依赖 fonttools + brotli（`pip install fonttools brotli`）。缺少依赖时会退回到
仓库里已生成的子集字体；再缺就只打印警告，构建继续使用系统字体。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

WEIGHTS = (400, 700)
FAMILY = "Noto Serif SC"
MANIFEST = "noto-serif-sc.chars.txt"

# 即使正文没出现，也要保证这些字符有字形（界面文案、标点、数字、拉丁字母）。
BASE_CHARS = (
    "".join(chr(c) for c in range(0x20, 0x7F))
    + "　、。，．；：？！“”‘’（）【】《》〈〉「」『』—…·～￥％＋－×÷＝"
    + "0123456789０１２３４５６７８９"
    + "目录封面下载阅读上一章下一章返回继续开始全书部分附录第章节页"
    + "主题浅色深色自动跟随系统跳转到正文菜单关闭打开正在加载"
)
BASE_CHARS = "".join(dict.fromkeys(BASE_CHARS))

SOURCE_CANDIDATES = [
    "NotoSerifSC-VariableFont_wght.ttf",
    "NotoSerifSC-Regular.otf",
    "NotoSerifSC-Regular.ttf",
    "NotoSerifSC[wght].ttf",
]


def log(msg: str) -> None:
    print(f"[fonts] {msg}", file=sys.stderr)


def font_target(out_dir: Path, weight: int) -> Path:
    return out_dir / f"noto-serif-sc-{weight}.woff2"


def find_source(explicit: str | None) -> Path | None:
    """按 配置 → 仓库内 → fontconfig → 常见路径 的顺序寻找字体源文件。"""
    if explicit:
        p = Path(explicit).expanduser()
        if p.is_file():
            return p
        log(f"指定的字体文件不存在：{p}")

    here = Path(__file__).resolve().parent.parent
    for pattern in ("*.ttf", "*.otf", "*.ttc", "*.woff2"):
        for p in sorted((here / "assets" / "fonts" / "src").glob(pattern)):
            return p

    try:
        out = subprocess.run(
            ["fc-match", "-f", "%{file}", FAMILY],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if out and Path(out).is_file() and Path(out).stat().st_size > 1_000_000:
            return Path(out)
    except (OSError, subprocess.SubprocessError):
        pass

    home = Path.home()
    for base in (
        home / "Library" / "Fonts",
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts"),
        Path("/usr/share/fonts"),
        home / ".local" / "share" / "fonts",
    ):
        for name in SOURCE_CANDIDATES:
            p = base / name
            if p.is_file():
                return p
        if base.is_dir():
            for p in base.rglob("NotoSerifSC*"):
                if p.suffix.lower() in {".ttf", ".otf"}:
                    return p
    return None


def load_font(source: Path):
    from fontTools.ttLib import TTFont

    try:
        return TTFont(str(source), lazy=False)
    except Exception:
        # 系统里常见的 .ttc 字体集合需要指定成员
        return TTFont(str(source), lazy=False, fontNumber=0)


def missing_chars(path: Path, chars: set[str]) -> set[str] | None:
    """检查已有子集缺了哪些字；无法检查时返回 None。"""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return None
    try:
        font = TTFont(str(path), lazy=True)
        cmap = font.getBestCmap() or {}
        font.close()
    except Exception:  # noqa: BLE001
        return None
    return {c for c in chars if ord(c) not in cmap}


def subset_and_save(font, chars: set[str], target: Path) -> bool:
    from fontTools import subset

    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.notdef_outline = True
    options.recalc_bounds = True
    options.drop_tables += ["DSIG", "EBDT", "EBLC", "EBSC", "SVG "]

    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text="".join(sorted(chars)))
    subsetter.subset(font)
    target.parent.mkdir(parents=True, exist_ok=True)
    font.save(str(target))
    return True


def build_weight(source: Path, weight: int, chars: set[str], target: Path) -> bool:
    """把源字体（可能是可变字体）实例化为指定字重，再子集化。"""
    from fontTools.varLib.instancer import instantiateVariableFont

    try:
        font = load_font(source)
    except Exception as exc:  # noqa: BLE001 - 字体损坏时不应中断发布会
        log(f"无法读取字体 {source}: {exc}")
        return False

    try:
        if "fvar" in font:
            font = instantiateVariableFont(
                font, {"wght": weight}, inplace=False, updateFontNames=True,
            )
        elif weight != 400:
            # 静态字体没有粗体源，交给浏览器合成
            return False
        return subset_and_save(font, chars, target)
    except Exception as exc:  # noqa: BLE001
        log(f"字体子集化失败（{weight}）：{exc}")
        return False
    finally:
        font.close()


def coverage_ok(targets: dict[int, Path], chars: set[str], manifest: Path) -> bool:
    if not all(p.is_file() for p in targets.values()):
        return False
    if manifest.is_file():
        recorded = set(manifest.read_text(encoding="utf-8"))
        return chars <= recorded
    missing = missing_chars(targets[400], chars)
    return missing is not None and not missing


def ensure_fonts(
    chars: set[str],
    out_dir: Path,
    cache_dir: Path,
    explicit: str | None = None,
) -> dict[int, Path]:
    """返回 {字重: woff2 路径}。找不到字体源时返回已提交的子集或空字典。"""
    chars = set(chars) | set(BASE_CHARS)
    targets = {w: font_target(out_dir, w) for w in WEIGHTS}
    manifest = out_dir / MANIFEST

    if coverage_ok(targets, chars, manifest):
        log(f"字体子集已覆盖全部 {len(chars)} 个用字")
        return {w: p for w, p in targets.items() if p.is_file()}

    missing = set()
    if targets[400].is_file() and manifest.is_file():
        missing = chars - set(manifest.read_text(encoding="utf-8"))
    if missing:
        log(f"字体子集缺少 {len(missing)} 个字符，重新生成：{''.join(sorted(missing))[:40]}")

    source = find_source(explicit)
    if source is None:
        ready = {w: p for w, p in targets.items() if p.is_file()}
        if ready:
            log("未找到字体源，沿用仓库内已生成的子集字体")
            return ready
        log("未找到 Noto Serif SC，网页/PDF 将回退到系统衬线字体")
        return {}

    log(f"从 {source} 生成子集字体（{len(chars)} 个字符）……")
    digest = hashlib.sha1("".join(sorted(chars)).encode()).hexdigest()[:16]
    digest += "-" + hashlib.sha1(str(source.stat().st_mtime_ns).encode()).hexdigest()[:8]

    produced: dict[int, Path] = {}
    for weight in WEIGHTS:
        cached = cache_dir / f"noto-serif-sc-{weight}-{digest}.woff2"
        if not cached.is_file():
            if not build_weight(source, weight, chars, cached):
                continue
        out_dir.mkdir(parents=True, exist_ok=True)
        target = targets[weight]
        shutil.copyfile(cached, target)
        produced[weight] = target

    if 400 not in produced:
        ready = {w: p for w, p in targets.items() if p.is_file()}
        return ready

    manifest.write_text("".join(sorted(chars)), encoding="utf-8")
    total = sum(p.stat().st_size for p in produced.values()) / 1024
    log(f"字体就绪：{', '.join(p.name for p in produced.values())}（共 {total:.0f} KB）")
    return produced


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chars-file", type=Path, action="append",
                    help="包含用字的文本文件，可重复")
    ap.add_argument("--out", type=Path, default=Path("docs/assets/fonts"))
    ap.add_argument("--cache", type=Path, default=Path(".cache/fonts"))
    ap.add_argument("--source", help="指定 Noto Serif SC 字体文件")
    ap.add_argument("--newsreader-source", help="指定 Newsreader 字体文件")
    args = ap.parse_args()

    chars = set(BASE_CHARS)
    for path in args.chars_file or []:
        if path.is_file():
            chars |= set(path.read_text(encoding="utf-8"))

    # 显式跑 make fonts 时强制重建
    for name in (MANIFEST, LATIN_MANIFEST):
        manifest = args.out / name
        if manifest.is_file():
            manifest.unlink()

    noto = ensure_fonts(chars, args.out, args.cache, args.source)
    latin = ensure_newsreader(chars, args.out, args.cache, args.newsreader_source)
    return 0 if (noto or latin) else 1


# --------------------------------------------------------------------------- #
# Newsreader（英文正文）
# --------------------------------------------------------------------------- #

LATIN_TARGETS = {
    (400, "normal"): "newsreader-400.woff2",
    (700, "normal"): "newsreader-700.woff2",
    (400, "italic"): "newsreader-400-italic.woff2",
}
LATIN_MANIFEST = "newsreader.chars.txt"


def find_newsreader(italic: bool = False, explicit: str | None = None) -> Path | None:
    if explicit:
        p = Path(explicit).expanduser()
        if p.is_file():
            return p
    names = [
        "Newsreader-Italic-VariableFont_opsz,wght.ttf" if italic else
        "Newsreader-VariableFont_opsz,wght.ttf",
        "Newsreader-Italic[wght].ttf" if italic else "Newsreader[wght].ttf",
        "Newsreader-Italic.ttf" if italic else "Newsreader-Regular.ttf",
    ]
    home = Path.home()
    for base in (home / "Library" / "Fonts", Path("/Library/Fonts"),
                 Path("/usr/share/fonts"), home / ".local" / "share" / "fonts"):
        for name in names:
            p = base / name
            if p.is_file():
                return p
        if base.is_dir():
            for p in base.rglob("Newsreader*"):
                if italic == ("Italic" in p.name) and p.suffix.lower() in {".ttf", ".otf"}:
                    return p
    try:
        pattern = "Newsreader:italic" if italic else "Newsreader"
        out = subprocess.run(["fc-match", "-f", "%{file}", pattern],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        if out and Path(out).is_file() and Path(out).stat().st_size > 50_000:
            return Path(out)
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def build_latin(source: Path, weight: int, style: str, chars: set[str], target: Path) -> bool:
    from fontTools.varLib.instancer import instantiateVariableFont

    try:
        font = load_font(source)
    except Exception as exc:  # noqa: BLE001
        log(f"无法读取字体 {source}: {exc}")
        return False
    try:
        if "fvar" in font:
            axes = {a.axisTag for a in font["fvar"].axes}
            location = {"wght": weight}
            if "opsz" in axes:
                location["opsz"] = 16
            font = instantiateVariableFont(font, location, inplace=False, updateFontNames=True)
        return subset_and_save(font, chars, target)
    except Exception as exc:  # noqa: BLE001
        log(f"Newsreader 子集化失败（{weight} {style}）：{exc}")
        return False
    finally:
        font.close()


def ensure_newsreader(chars: set[str], out_dir: Path, cache_dir: Path,
                      explicit: str | None = None) -> dict[tuple[int, str], Path]:
    """返回 {(weight, style): woff2 路径}；缺字体源时沿用已提交的子集。"""
    chars = {c for c in chars if ord(c) < 0x2E80} | set(BASE_CHARS)
    chars = {c for c in chars if ord(c) < 0x2E80}
    targets = {key: out_dir / name for key, name in LATIN_TARGETS.items()}
    manifest = out_dir / LATIN_MANIFEST

    if all(p.is_file() for p in targets.values()):
        recorded = set(manifest.read_text(encoding="utf-8")) if manifest.is_file() else None
        if recorded is None or chars <= recorded:
            log(f"Newsreader 子集已覆盖 {len(chars)} 个用字")
            return {k: p for k, p in targets.items() if p.is_file()}

    regular = find_newsreader(False, explicit)
    italic = find_newsreader(True, explicit)
    if regular is None and not any(p.is_file() for p in targets.values()):
        log("未找到 Newsreader，英文将回退到系统衬线字体")
        return {}

    log(f"生成 Newsreader 子集（{len(chars)} 个字符）……")
    digest = hashlib.sha1("".join(sorted(chars)).encode()).hexdigest()[:16]
    produced: dict[tuple[int, str], Path] = {}
    for (weight, style), target in targets.items():
        source = italic if style == "italic" else regular
        if source is None:
            continue
        cached = cache_dir / f"{target.stem}-{digest}.woff2"
        if not cached.is_file() and not build_latin(source, weight, style, chars, cached):
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cached, target)
        produced[(weight, style)] = target

    if produced:
        manifest.write_text("".join(sorted(chars)), encoding="utf-8")
        total = sum(p.stat().st_size for p in produced.values()) / 1024
        log(f"字体就绪：{', '.join(p.name for p in produced.values())}（共 {total:.0f} KB）")
    return produced or {k: p for k, p in targets.items() if p.is_file()}


if __name__ == "__main__":
    raise SystemExit(main())
