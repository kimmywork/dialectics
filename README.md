# 《走出二选一》/ Beyond Either/Or 发布框架

一部书，两个语言版本，三种输出：

- **双语落地页** `docs/index.html` —— 按浏览器语言自动显示中文或英文，PDF / EPUB 下载只在这里出现。
- **中文阅读站** `docs/zh/` —— 分章阅读、目录侧栏、深浅色、阅读进度与续读。
- **英文阅读站** `docs/en/` —— 同样的阅读体验，正文使用 Newsreader。
- **PDF / EPUB** —— 每个语言各一份，A4 书籍版式与电子书版式。

正文只有两个 Markdown 源文件，构建时自动拆成「部分 / 章节」。产物直接写回 `docs/`，提交后用 GitHub Pages 发布，不需要云端构建。

## 快速开始

```bash
# 依赖：pandoc、Python 3.11+、本机 Chrome（用于打印 PDF）
# 建议：pip install -r requirements.txt
#       —— pypdf 生成 PDF 书签；fonttools + brotli 生成字体子集

make            # 构建中英网页、两份 PDF 与两份 EPUB
make web        # 只构建网页
make pdf        # 重建两份 PDF（同时刷新网页）
make epub       # 构建网页 + EPUB（跳过 PDF）
make serve      # 本地预览 http://localhost:8000
make clean      # 删除生成文件与缓存，保留源文件和 assets
make fonts      # 重新生成中文 / 英文字体子集
make check      # 语法检查 build.py 与 scripts/
```

构建完成后：

| 路径 | 内容 |
| --- | --- |
| `docs/index.html` | 双语落地页（语言切换、下载入口） |
| `docs/zh/index.html` | 中文阅读首页 |
| `docs/en/index.html` | 英文阅读首页 |
| `docs/zh/ch01.html` … | 中文章节页（`part-*.html` 为部分扉页） |
| `docs/en/ch01.html` … | 英文章节页 |
| `docs/zh/dialectics.pdf` · `en/` | 两份 PDF |
| `docs/zh/dialectics.epub` · `en/` | 两份 EPUB |
| `docs/assets/` | 样式、脚本、字体（源文件，直接发布） |
| `markdown/dialectics.md` | 中文源稿 |
| `markdown/dialectics_en.md` | 英文源稿 |
| `AGENTS.md` | 给编码 Agent 的仓库操作说明 |

## 目录结构

```
book.toml                 站点信息与两个语言的 edition 配置
build.py                  构建入口：解析 → 渲染 → 网页 → PDF → 书签 → EPUB
scripts/prepare_fonts.py  Noto Serif SC 与 Newsreader 的静态字重子集化
scripts/pdf_toc.py        按标题定位页码，写入三层 PDF 书签
scripts/latex_text.py     LaTeX → Unicode 纯文本（EPUB 用）
templates/                网页外壳 / 打印外壳 / 双语落地页
markdown/                 中英文正文源文件
docs/index.html           双语落地页（生成物）
docs/zh/ docs/en/         两个语言的阅读站与下载文件（生成物）
docs/assets/              样式、脚本、字体（源文件，直接发布）
LICENSE.md                许可协议全文
```

## 双语与发布结构

- 落地页在 `docs/index.html`：读取 `localStorage` 中保存的语言偏好，否则按 `navigator.language` 选择中文或英文；右上角可手动切换，选择会记住。
- 两个阅读站的页头、侧栏都有语言切换链接（`English` / `中文`），互相跳转到对方的首页。
- **PDF / EPUB 下载只在落地页**。阅读首页与侧栏不再放出下载按钮，避免阅读页出现与当前语言不一致的文件。
- 新增一个语言版本：在 `book.toml` 增加一个 `[editions.xx]`，放入对应源文件，重新 `make`。输出目录、导航、字体与书签会按 `code` 自动生成。

## 改写正文的约定

- `# ` 是一级结构（部分 / 附录），`## ` 是章节，`### ` 及以下是节与小节。
- 章节标题前的 `★` 表示入门核心章节，构建时变成独立星标，不影响目录编号对齐。
- 章节标题末尾的 `（如何……）` 或 `(How to ...)` 会自动拆成下一行的浅色副标题，正文、目录、PDF 与 EPUB 同步。
- 列表前留一个空行。紧跟段落的 `*` 列表虽然也能解析，但容易和其他 Markdown 语法混淆。
- 数学公式用单反斜杠（`\frac`、`\rho`）。源文件里如果混入制表符、换页符等控制字符，构建会告警——这通常意味着 LaTeX 被复制/转义破坏了。
- 英文正文里的货币 `$` 需要写成 `\$`，否则会和公式分隔符混淆。
- 标题里可以用 `*斜体*`；构建会在标题与目录里正确区分强调与普通文字。
- 新增章节后如果出现字体子集没有的字，构建会提示，运行 `make fonts` 重新生成。

## 字体

- **中文 Web**：通过 **Fontsource CDN**（jsDelivr）加载 Noto Serif SC。CSS 按 `unicode-range` 拆成上百个分包，浏览器只下载当前页面用到的块；网页只加载 400 字重，标题与加粗用合成粗体，首屏约 1.2 MB（含 CSS），后续页面直接命中缓存。仓库里不存放中文字体。
- **中文 PDF**：构建时从系统 Noto Serif SC 生成 400/700 子集到 `build/fonts/`（不入库），嵌入 PDF。换机器构建需要本机安装 Noto Serif SC。
- **英文**：Newsreader 的 Regular / Bold / Italic 子集（约 100 KB）随仓库提交，供网页、PDF 与 EPUB 共用；EPUB 内嵌该字体。
- **中英混排**：字体栈统一为 `"Newsreader", "Noto Serif SC", …`，拉丁字母与数字用 Newsreader，汉字回退 Noto；中文页面也会预加载 Newsreader。
- CDN 地址在 `book.toml` 的 `[fonts] chinese_cdn`；`web_bold = false` 控制网页是否额外加载 700 分包（打开会多约 1 MB）。

字体查找顺序：`book.toml` 指定文件 → `docs/assets/fonts/src/` → 系统字体目录 → `fc-match`。PDF 字体必须实例化成静态字重：Chromium 的 PDF 后端无法嵌入可变字体，会把字形降级成 Type3 路径，PDF 会从几 MB 膨胀到二十多 MB。

## 发布到 GitHub Pages

1. 提交并推送 `docs/`；
2. 仓库 **Settings → Pages → Build and deployment**：Source 选 **Deploy from a branch**，分支 `master`，目录 **`/docs`**；
3. 自定义域名写在 `docs/CNAME`（`dialectics.kimleo.net`），DNS 加一条 `dialectics` → `<user>.github.io` 的 CNAME 记录；
4. 等证书签发，访问 `https://dialectics.kimleo.net/`。

站点内部全部使用相对链接，自定义域名与项目页路径都能正常工作。`.nojekyll` 已放在 `docs/` 下，GitHub 按原样提供文件，不做 Jekyll 处理。

## 实现要点

- **pandoc** 负责 Markdown → HTML，网页与 PDF 的公式输出为 **MathML**。
- **Chromium** 打印 PDF：`@page` 命名页 + 边距框实现封面底色、部分扉页不显示页码、正文页眉与页码。
- **pypdf** 补写阅读器侧边栏书签（部分 → 章节 → 小节）；书页目录保持干净、不排页码。
- **EPUB** 由 pandoc 输出；微信读书等阅读器不渲染 MathML，公式在打包前转成 Unicode 文本。
- **落地页**是纯静态 HTML + 一小段 JS，语言选择立即生效并持久化，无需后端。
- 站点无第三方 JS 依赖；中文字体走 jsDelivr CDN（Fontsource 分包），英文与 PDF 字体本地生成或内嵌。

## 维护检查

```bash
make check      # Python 语法
make            # 三种格式、两个语言都能生成
```

发布前确认：

1. 落地页按浏览器语言显示对应版本，手动切换后刷新仍保持；
2. 中英文阅读站都能打开，侧栏语言链接互跳正确；
3. 阅读页没有 PDF / EPUB 下载链接，下载只在落地页；
4. PDF 封面一页，书签为「部分 → 章节 → 小节」三层；
5. EPUB 用微信读书或 Apple Books 打开，公式、代码、表格与目录正常（阅读器会缓存旧文件，需删除后重新导入）；
6. 提交内容不含本机路径或用户名：
   `git grep -n "qliu23\|/Users/" docs`

## 许可

正文采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans)：个人使用免费，商业培训、教学、付费课程与商业出版需联系作者授权。协议全文见 `LICENSE.md` 与书中附录 E。
