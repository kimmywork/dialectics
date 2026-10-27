PY ?= python3
PORT ?= 8000

.PHONY: all web pdf epub serve clean fonts check

all:            ## 构建网页 + PDF（输出到 docs/）
	$(PY) build.py

web:            ## 只构建网页
	$(PY) build.py --no-pdf

pdf:            ## 重建 PDF（PDF 同时放在 docs/ 供站内下载）
	$(PY) build.py

epub:           ## 构建网页 + EPUB（跳过 PDF）
	$(PY) build.py --no-pdf

serve:          ## 本地预览 http://localhost:8000
	$(PY) build.py --no-pdf
	@echo "→ http://localhost:$(PORT)/"
	@$(PY) -m http.server $(PORT) --directory docs

fonts:          ## 按当前正文重新生成字体子集
	$(PY) scripts/prepare_fonts.py --chars-file docs/dialectics.md --out docs/assets/fonts

clean:          ## 删除生成页面与缓存，保留源文件与 assets
	$(PY) build.py --clean

check:
	$(PY) -m py_compile build.py scripts/prepare_fonts.py scripts/pdf_toc.py
