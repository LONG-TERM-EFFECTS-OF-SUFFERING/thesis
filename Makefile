MAIN        := main
TEX_FILES   := $(shell find . -type f -name '*.tex' -not -path './build/*')
BUILD_DIR   := build

LATEXMK     := latexmk
LATEXINDENT := latexindent
CHKTEX      := chktex

CHKTEX_NOWARN := -n 1 -n 12 -n 13 -n 24 -n 36 -n 37

.PHONY: all build watch format format-check lint lint-tex check clean clean-indent-tmp help

all: build

build:
	$(LATEXMK) $(MAIN).tex
watch:
	$(LATEXMK) -pvc $(MAIN).tex
format:
	@for f in $(TEX_FILES); do \
		echo "  latexindent  $$f"; \
		$(LATEXINDENT) -s -w -m -l "$$f" || { $(MAKE) -s clean-indent-tmp; exit 1; }; \
	done
	@$(MAKE) -s clean-indent-tmp
format-check:
	@status=0; \
	for f in $(TEX_FILES); do \
		$(LATEXINDENT) -s -m -l -k "$$f" >/dev/null 2>&1 || { \
			echo "NEEDS FORMAT: $$f"; status=1; \
		}; \
	done; \
	$(MAKE) -s clean-indent-tmp; \
	exit $$status
clean-indent-tmp:
	@find . -type f \( -name '*.bak' -o -name '*.bak[0-9]' -o -name '*.tmp.bak' -o -name '*.tmp.tex' \) \
		-not -path './build/*' -not -path './.git/*' -delete
lint: lint-tex
lint-tex:
	@status=0; \
	for f in $(TEX_FILES); do \
		$(CHKTEX) -q -I0 -l .chktexrc $(CHKTEX_NOWARN) "$$f" || status=1; \
	done; \
	exit $$status
check: format-check lint build
clean: clean-indent-tmp
	$(LATEXMK) -C
	rm -rf $(BUILD_DIR) _minted-* sources.md
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'
