# 《走出二选一》发布框架

一份 Markdown 原稿，两条发布通道：

- **Web** —— 分章阅读的静态站点，带目录侧栏、深浅色、阅读进度和续读。
- **PDF** —— A4 书籍版式，含封面、说明页、目录、部分扉页、页眉页码，以及阅读器侧边栏书签。

正文只有 `docs/dialectics.md` 一个源文件，构建时自动按一级/二级标题拆成「部分」和「章节」。构建产物直接写回 `docs/`，提交后用 GitHub Pages 发布即可，不需要在云端构建。

## 快速开始

```bash
# 依赖：pandoc、Python 3.11+、本机 Chrome（用于打印 PDF）
# 建议：pip install -r requirements.txt
#       —— pypdf 生成 PDF 侧边栏书签；fonttools + brotli 生成字体子集

make            # 构建 docs/ 下的全部页面和 PDF
make web        # 只构建网页
make serve      # 本地预览 http://localhost:8000
make clean      # 只清理生成文件，保留源文件与 assets
```

构建完成后：

| 路径 | 内容 |
| --- | --- |
| `docs/index.html` | 封面与目录首页 |
| `docs/ch01.html` … | 各章节页面（`part-*.html` 为部分扉页） |
| `docs/dialectics.pdf` | 可下载的 PDF |
| `docs/assets/` | 样式、脚本、字体（源文件，直接发布） |
| `docs/dialectics.md` | 正文源文件 |

## 目录结构

```
book.toml                 书名、副标题、描述、源文件路径等
build.py                  构建入口：解析 → pandoc → 网页 → PDF → 书签
scripts/prepare_fonts.py  查找系统字体并按用字子集化为 woff2
scripts/pdf_toc.py        按标题定位页码并写入 PDF 书签
templates/layout.html     网页外壳
templates/print.html      PDF 外壳
docs/assets/css/base.css  共用排版与配色变量
docs/assets/css/web.css   三栏阅读器布局
docs/assets/css/print.css A4 分页、页眉页码、封面与扉页
docs/assets/js/app.js     主题、抽屉目录、进度条、续读、键盘翻页
docs/assets/fonts/        子集化后的 Noto Serif SC（随仓库提交）
docs/dialectics.md        正文源文件
```

## 改内容 / 改版式

- **改正文**：直接编辑 `docs/dialectics.md`。`# ` 是一级结构（部分/附录），`## ` 是章节，`### ` 及以下为节与小节。新增章节后如果出现字体子集没有的字，构建会提示，`make fonts` 重新生成即可。
- **改书名、描述、作者**：编辑 `book.toml`。作者留空则不显示。
- **改配色与字号**：`docs/assets/css/base.css` 顶部的 CSS 变量。
- **改 PDF 版式**：`docs/assets/css/print.css`；页眉里的书名来自 `book.toml`（`__BOOK_TITLE__` 占位符在构建时替换）。
- **改网页结构**：`templates/layout.html` 与 `build.py` 里的 `build_site()`。

## 字体

正文使用 **Noto Serif SC**，按本书实际用字子集化为两个静态字重（Regular / Bold，各约 1.2 MB），网页和 PDF 共用同一份文件：

1. 优先使用 `book.toml` 中 `[fonts] source` 指定的文件；
2. 否则在 `docs/assets/fonts/src/`、系统字体目录、`fc-match "Noto Serif SC"` 中查找；
3. 都没有则沿用仓库里已提交的子集字体；再没有就回退到系统宋体并给出提示。

子集字体由 fontTools 生成（`make fonts`），采用 SIL Open Font License。之所以实例化成静态字重而不是直接使用可变字体，是因为 Chromium 的 PDF 后端无法嵌入可变字体，会把每个字形降级成 Type3 路径字体，整本书的 PDF 会从 4 MB 膨胀到 24 MB。

## 发布到 GitHub Pages

构建产物已经在 `docs/` 里，直接提交即可：

1. 提交并推送 `docs/` 目录；
2. 仓库 **Settings → Pages → Build and deployment**：Source 选 **Deploy from a branch**，分支选 `master`，目录选 **`/docs`**；
3. 自定义域名已写在 `docs/CNAME`（`dialectics.kimleo.net`），并在 DNS 里加一条
   `dialectics` → `<user>.github.io` 的 CNAME 记录；
4. 等证书签发完成，访问 `https://dialectics.kimleo.net/`。

站点内部全部使用相对链接，自定义域名与项目页路径都能正常工作。`.nojekyll` 已放在 `docs/` 下，GitHub 会按原样提供文件，不做 Jekyll 处理。

## 实现要点

- **pandoc** 负责 Markdown → HTML，数学公式输出为 **MathML**，网页和 PDF 都不依赖 MathJax/KaTeX 运行时。
- **Chromium** 的 print-to-pdf 负责 PDF：CSS `@page` 命名页 + 边距框实现封面底色、部分扉页不显示页码、正文页眉与页码。
- **pypdf** 在打印完成后补写阅读器侧边栏的嵌套书签（部分 → 章节）。印在书页里的目录保持干净，不排页码。
- **构建顺序**：解析 → 渲染 → 统计用字 → 子集字体 → 写出页面 → 生成打印页 → 打印 PDF → 写入书签。
- 站点无第三方 JS/CSS 依赖，离线可读（字体随站点分发）。
