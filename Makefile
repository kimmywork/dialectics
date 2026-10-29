PY ?= python3
PORT ?= 8000

.PHONY: all web pdf epub serve clean fonts check verify verify-full test-setup test-ui test-update

all:            ## 构建网页 + PDF + EPUB（输出到 docs/）
	$(PY) build.py

web:            ## 只构建网页
	$(PY) build.py --no-pdf --no-epub

pdf:            ## 构建网页 + PDF（跳过 EPUB）
	$(PY) build.py --no-epub

epub:           ## 构建网页 + EPUB（跳过 PDF）
	$(PY) build.py --no-pdf

serve:          ## 本地预览 http://localhost:8000
	$(PY) build.py --no-pdf --no-epub
	@echo "→ http://localhost:$(PORT)/"
	@$(PY) -m http.server $(PORT) --directory docs

fonts:          ## 按当前正文重新生成中英文字体子集
	$(PY) scripts/prepare_fonts.py --chars-file markdown/dialectics.md --chars-file markdown/dialectics_en.md --out build/fonts

clean:          ## 删除生成页面与缓存，保留源文件与 assets
	$(PY) build.py --clean

check:
	$(PY) -m py_compile build.py scripts/*.py

verify: web     ## 网页构建 + 产物检查 + Playwright 回归
	$(PY) scripts/verify_artifacts.py
	npm test

verify-full: all ## 全量构建（含 PDF/EPUB）+ 产物检查 + Playwright 回归
	$(PY) scripts/verify_artifacts.py
	npm test

test-setup:     ## 安装 Node 依赖与 Playwright Chromium
	npm install
	npx playwright install chromium

test-ui:        ## 打开 Playwright 交互式调试
	npm run test:ui

test-update:    ## 重新生成视觉回归基线（检查 diff 后再提交）
	npm run test:update
