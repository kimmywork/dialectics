"""把书中的 LaTeX 公式转成 Unicode 纯文本，供 EPUB 使用。

微信读书等阅读器不渲染 MathML，<math> 会直接消失。本书公式以符号、比例和
上下标为主，转成 Unicode 后既能在任何阅读器显示，也能被搜索和朗读。
"""

from __future__ import annotations

import html
import re

SYMBOLS = {
    "rightarrow": "→", "leftarrow": "←", "leftrightarrow": "↔",
    "longleftrightarrow": "⟷", "longrightarrow": "⟶", "dashrightarrow": "⇢",
    "Rightarrow": "⇒", "Leftarrow": "⇐", "to": "→",
    "neg": "¬", "land": "∧", "lor": "∨", "cup": "∪", "cap": "∩",
    "cdot": "·", "times": "×", "div": "÷", "pm": "±", "mp": "∓",
    "dots": "…", "ldots": "…", "cdots": "⋯",
    "approx": "≈", "ge": "≥", "geq": "≥", "le": "≤", "leq": "≤",
    "neq": "≠", "equiv": "≡", "circ": "∘", "propto": "∝", "vdash": "⊢",
    "langle": "⟨", "rangle": "⟩", "prod": "∏", "sum": "∑",
    "infty": "∞", "in": "∈", "notin": "∉", "subset": "⊂",
    "therefore": "∴", "because": "∵", "emptyset": "∅",
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "Delta": "Δ",
    "epsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "Theta": "Θ",
    "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν",
    "xi": "ξ", "pi": "π", "rho": "ρ", "sigma": "σ", "Sigma": "Σ",
    "tau": "τ", "upsilon": "υ", "phi": "φ", "chi": "χ", "psi": "ψ",
    "omega": "ω", "Omega": "Ω",
}

SUB = str.maketrans(
    "0123456789+-=()aehijklmnoprstuvx",
    "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ",
)
SUP = str.maketrans(
    "0123456789+-=()niktx",
    "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱᵏᵗˣ",
)
SUB_CHARS = set("0123456789+-=()aehijklmnoprstuvx")
SUP_CHARS = set("0123456789+-=()niktx")

FUNCTIONS = {"max", "min", "log", "ln", "exp", "sin", "cos", "tan", "lim", "sup", "inf"}
IGNORED = {"left", "right", "big", "Big", "bigg", "Bigg", "displaystyle",
           "textstyle", "quad", "qquad", "!", ",", ";", ":", " "}
TEXT_COMMANDS = {"text", "mathrm", "mathbf", "mathbb", "mathcal", "operatorname", "mbox"}


def _read_arg(src: str, i: int) -> tuple[str, int]:
    """读取命令参数：{...} 或单个字符。"""
    while i < len(src) and src[i] == " ":
        i += 1
    if i >= len(src):
        return "", i
    if src[i] == "{":
        depth = 0
        for j in range(i, len(src)):
            if src[j] == "{":
                depth += 1
            elif src[j] == "}":
                depth -= 1
                if depth == 0:
                    return convert(src[i + 1:j]), j + 1
        return convert(src[i + 1:]), len(src)
    return convert(src[i]), i + 1


def _script(arg: str, table, allowed: set[str]) -> str | None:
    compact = arg.replace(" ", "")
    if compact and all(ch in allowed for ch in compact):
        return compact.translate(table)
    return None


def _fraction(a: str, b: str) -> str:
    def wrap(part: str) -> str:
        return f"({part})" if re.search(r"[+\-·\s]", part) else part
    return f"{wrap(a)}/{wrap(b)}"


def convert(tex: str, report: set[str] | None = None) -> str:
    out: list[str] = []
    i = 0
    while i < len(tex):
        ch = tex[i]
        if ch == "\\":
            nxt = tex[i + 1] if i + 1 < len(tex) else ""
            if nxt in "{}%$&#_":
                out.append(nxt)
                i += 2
                continue
            match = re.match(r"\\([A-Za-z]+)", tex[i:])
            if not match:
                i += 2
                continue
            name = match.group(1)
            i += match.end()
            # TeX 会吞掉控制词后面的空格，这里保持一致（\Delta I → ΔI）
            while i < len(tex) and tex[i] == " ":
                i += 1

            if name == "vec":
                arg, i = _read_arg(tex, i)
                out.append(arg + "\u20d7")
            elif name == "bar":
                arg, i = _read_arg(tex, i)
                out.append(arg + "\u0305")
            elif name == "frac":
                a, i = _read_arg(tex, i)
                b, i = _read_arg(tex, i)
                out.append(_fraction(a, b))
            elif name in TEXT_COMMANDS:
                arg, i = _read_arg(tex, i)
                out.append(arg)
            elif name in FUNCTIONS:
                out.append(name)
            elif name in IGNORED:
                if name in {"quad", "qquad", " "}:
                    out.append(" ")
            else:
                if name not in SYMBOLS and report is not None:
                    report.add(name)
                out.append(SYMBOLS.get(name, name))
        elif ch in "_^":
            arg, i = _read_arg(tex, i + 1)
            mapped = _script(arg, SUB if ch == "_" else SUP,
                             SUB_CHARS if ch == "_" else SUP_CHARS)
            out.append(mapped if mapped else arg)
        elif ch in "{}":
            i += 1
        elif ch == "~":
            out.append(" ")
            i += 1
        elif ch == "&":
            out.append(" ")
            i += 1
        else:
            out.append(ch)
            i += 1

    text = re.sub(r"\s+", " ", "".join(out))
    # 去掉括号内侧与标点前的多余空格：⟨ k ⟩ → ⟨k⟩
    text = re.sub(r"\s+([)\]}>⟩,.;:])", r"\1", text)
    text = re.sub(r"([(\[{⟨])\s+", r"\1", text)
    # TeX 会吞掉控制词后的空格，但纯文本里运算符两侧需要留白
    for op in "≈≥≤=≠×·±→↔⟷⟶⇢∧∨+-":
        text = re.sub(rf"\s*{re.escape(op)}\s*", f" {op} ", text)
    return re.sub(r"\s+", " ", text).strip()


def to_html(tex: str, display: bool = False, report: set[str] | None = None) -> str:
    """把公式转成带样式的文本片段。"""
    body = html.escape(convert(tex, report))
    if display:
        return f'<span class="math-display">{body}</span>'
    return f'<span class="math-text">{body}</span>'
