# 《走出二选一》发布框架

一份 Markdown 原稿，三条发布通道：

- **Web** —— 分章阅读的静态站点，带目录侧栏、深浅色、阅读进度和续读。
- **PDF** —— A4 书籍版式，含封面、说明页、目录、部分扉页、页眉页码，以及三层阅读器书签。
- **EPUB** —— 带封面与完整目录的电子书，适配微信读书、Apple Books、Kindle 等阅读器。

正文只有 `docs/dialectics.md` 一个源文件，构建时自动按一级/二级标题拆成「部分」和「章节」。构建产物直接写回 `docs/`，提交后用 GitHub Pages 发布，不需要在云端构建。

## 快速开始

```bash
# 依赖：pandoc、Python 3.11+、本机 Chrome（用于打印 PDF）
# 建议：pip install -r requirements.txt
#       —— pypdf 生成 PDF 书签；fonttools + brotli 生成字体子集

make            # 构建网页、PDF 与 EPUB
make web        # 只构建网页
make pdf        # 重建 PDF（同时刷新网页）
make epub       # 构建网页 + EPUB（跳过 PDF）
make serve      # 本地预览 http://localhost:8000
make clean      # 删除生成文件与缓存，保留源文件和 assets
make check      # 语法检查 build.py 与 scripts/
```

构建完成后：

| 路径 | 内容 |
| --- | --- |
| `docs/index.html` | 封面与目录首页 |
| `docs/ch01.html` … | 各章节页面（`part-*.html` 为部分扉页） |
| `docs/dialectics.pdf` | 可下载的 PDF |
| `docs/dialectics.epub` | 可下载的 EPUB |
| `docs/assets/` | 样式、脚本、字体（源文件，直接发布） |
| `docs/dialectics.md` | 正文源文件 |
| `AGENTS.md` | 给编码 Agent 的仓库操作说明 |

## 目录结构

```
book.toml                 书名、副标题、作者、主页、许可、源文件路径
build.py                  构建入口：解析 → pandoc → 网页 → PDF → 书签 → EPUB
scripts/prepare_fonts.py  查找系统字体，实例化静态字重并按用字子集化为 woff2
scripts/pdf_toc.py        按标题定位页码，写入三层 PDF 书签
scripts/latex_text.py     LaTeX → Unicode 纯文本（EPUB 用）
templates/layout.html     网页外壳
templates/print.html      PDF 外壳
docs/assets/css/base.css  共用排版与配色变量
docs/assets/css/web.css   三栏阅读器布局
docs/assets/css/print.css A4 分页、页眉页码、封面与扉页
docs/assets/css/epub.css  EPUB 阅读样式
docs/assets/js/app.js     主题、抽屉目录、进度条、续读、键盘翻页
docs/assets/fonts/        子集化后的 Noto Serif SC（随仓库提交）
docs/dialectics.md        正文源文件
LICENSE.md                许可协议全文
AGENTS.md                 给编码 Agent 的仓库操作说明（英文）
```

## 改写正文的约定

- `# ` 是一级结构（部分 / 附录），`## ` 是章节，`### ` 及以下是节与小节。
- 章节标题前的 `★` 表示入门核心章节。构建时会把它变成独立的星标，不影响目录编号对齐。
- 章节标题末尾的 `（如何……）` 会自动拆成下一行的浅色副标题，正文、目录、PDF 与 EPUB 同步。
- 列表前留一个空行。行内紧跟段落的 `*` 列表虽然也能解析，但容易和其他 Markdown 语法混淆。
- 数学公式用单反斜杠（`\frac`、`\rho`）。源文件里如果混入制表符、换页符等控制字符，构建会告警——这通常意味着 LaTeX 被某次复制/转义破坏了。
- 新增章节后如果出现字体子集没有的字，构建会提示，运行 `make fonts` 重新生成。

## 改配置 / 改版式

- **书名、作者、主页、许可**：`book.toml`；作者留空则不显示署名。
- **配色与字号**：`docs/assets/css/base.css` 顶部的 CSS 变量。
- **PDF 版式**：`docs/assets/css/print.css`；页眉书名由构建时替换 `book.toml` 里的占位符。
- **EPUB 样式**：`docs/assets/css/epub.css`。
- **网页结构**：`templates/layout.html` 与 `build.py` 的 `build_site()`。

`docs/` 下的 HTML、PDF、EPUB 都是生成物，不要手改；改源文件或模板后重新 `make`。

## 字体

正文使用 **Noto Serif SC**，按本书实际用字子集化为两个静态字重（Regular / Bold，各约 1.2 MB），网页和 PDF 共用同一份文件：

1. 优先使用 `book.toml` 中 `[fonts] source` 指定的文件；
2. 否则在 `docs/assets/fonts/src/`、系统字体目录、`fc-match "Noto Serif SC"` 中查找；
3. 都没有则沿用仓库里已提交的子集字体；再没有就回退到系统宋体并给出提示。

子集字体由 fontTools 生成（`make fonts`），采用 SIL Open Font License。必须实例化成静态字重：Chromium 的 PDF 后端无法嵌入可变字体，会把每个字形降级成 Type3 路径，整本书的 PDF 会从 4 MB 膨胀到 24 MB。

## 发布到 GitHub Pages

构建产物已经在 `docs/` 里，直接提交即可：

1. 提交并推送 `docs/`；
2. 仓库 **Settings → Pages → Build and deployment**：Source 选 **Deploy from a branch**，分支选 `master`，目录选 **`/docs`**；
3. 自定义域名写在 `docs/CNAME`（`dialectics.kimleo.net`），DNS 加一条 `dialectics` → `<user>.github.io` 的 CNAME 记录；
4. 等证书签发完成，访问 `https://dialectics.kimleo.net/`。

站点内部全部使用相对链接，自定义域名与项目页路径都能正常工作。`.nojekyll` 已放在 `docs/` 下，GitHub 会按原样提供文件，不做 Jekyll 处理。

## 实现要点

- **pandoc** 负责 Markdown → HTML，网页与 PDF 的公式输出为 **MathML**，不依赖 MathJax/KaTeX 运行时。
- **Chromium** 的 print-to-pdf 负责 PDF：CSS `@page` 命名页 + 边距框实现封面底色、部分扉页不显示页码、正文页眉与页码。
- **pypdf** 在打印完成后补写阅读器侧边栏书签（部分 → 章节 → 小节），书页里的目录保持干净、不排页码。
- **EPUB** 由 pandoc 输出，自动生成封面 PNG 和可点击目录。微信读书等阅读器不渲染 MathML，公式会在打包前转成 Unicode 纯文本（`\frac{a}{b}` → `a/b`，上下标、希腊字母、箭头都保留）。
- **构建顺序**：解析 → 渲染 → 统计用字 → 子集字体 → 写出页面 → 生成打印页 → 打印 PDF → 写入书签 → 打包 EPUB。
- 站点无第三方 JS/CSS 依赖，离线可读（字体随站点分发）。

## 维护检查

改完正文或样式后，至少跑一遍：

```bash
make check      # Python 语法
make            # 三种格式都能生成
```

发布前再确认：

1. PDF 封面只有一页，目录、部分扉页和章节起页正常；
2. PDF 阅读器侧边栏能看到「部分 → 章节 → 小节」三层书签；
3. EPUB 用微信读书或 Apple Books 打开，公式、代码、表格和目录都能显示（阅读器会缓存旧文件，需删除后重新导入）；
4. 提交内容不包含本机路径或用户名：
   `git grep -n "qliu23\|/Users/" docs`

## 许可

正文采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans)：个人使用免费，商业培训、教学、付费课程与商业出版需联系作者授权。协议全文见 `LICENSE.md` 与书中附录 E。
