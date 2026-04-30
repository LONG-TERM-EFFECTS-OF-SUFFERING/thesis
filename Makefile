MAIN        := main
TEX_FILES   := $(shell find . -type f -name '*.tex' -not -path './build/*')
BUILD_DIR   := build

LATEXMK     := latexmk
LATEXINDENT := latexindent
CHKTEX      := chktex

# Warnings silenced project-wide. See `man chktex` for the full list.
#   -n 1  : "Command terminated with space."  (style: \left, \right and other \cmd followed by space)
#   -n 12 : "Interword spacing (`\\ ') should perhaps be used."  (pedantic, after Mr./Dr.)
#   -n 13 : "Intersentence spacing (`\\@') should perhaps be used."  (pedantic)
#   -n 24 : "Delete this space to maintain correct pagereferences."  (pre-`\label` whitespace; sub-pixel)
#   -n 36 : "You should put a space in front of parenthesis."  (false positives with \cite/text(s))
#   -n 37 : "You should avoid spaces in front of parenthesis."  (style: \left ( and \right ))
CHKTEX_NOWARN := -n 1 -n 12 -n 13 -n 24 -n 36 -n 37

.PHONY: all build watch format format-check lint lint-tex check clean clean-indent-tmp help

all: build

## build: Compile the thesis once with latexmk (reads .latexmkrc).
build:
	$(LATEXMK) $(MAIN).tex

## watch: Continuous build with preview (latexmk -pvc).
watch:
	$(LATEXMK) -pvc $(MAIN).tex

## format: Rewrite all .tex files with latexindent.
format:
	@for f in $(TEX_FILES); do \
		echo "  latexindent  $$f"; \
		$(LATEXINDENT) -s -w -m -l "$$f" || { $(MAKE) -s clean-indent-tmp; exit 1; }; \
	done
	@$(MAKE) -s clean-indent-tmp

## format-check: Fail if any .tex file is not latexindent-clean (CI gate).
format-check:
	@status=0; \
	for f in $(TEX_FILES); do \
		$(LATEXINDENT) -s -m -l -k "$$f" >/dev/null 2>&1 || { \
			echo "NEEDS FORMAT: $$f"; status=1; \
		}; \
	done; \
	$(MAKE) -s clean-indent-tmp; \
	exit $$status

# Remove latexindent backups and check-mode temp files (.bak, .bak0/1/2, .tmp.bak, .tmp.tex).
clean-indent-tmp:
	@find . -type f \( -name '*.bak' -o -name '*.bak[0-9]' -o -name '*.tmp.bak' -o -name '*.tmp.tex' \) \
		-not -path './build/*' -not -path './.git/*' -delete

## lint: Run ChkTeX on every .tex file.
lint: lint-tex

lint-tex:
	@status=0; \
	for f in $(TEX_FILES); do \
		$(CHKTEX) -q -I0 -l .chktexrc $(CHKTEX_NOWARN) "$$f" || status=1; \
	done; \
	exit $$status

## check: format-check + lint + build. Use this in CI.
check: format-check lint build

## clean: Remove all build artifacts (latexmk -C plus minted/indent backups).
clean: clean-indent-tmp
	$(LATEXMK) -C
	rm -rf $(BUILD_DIR) _minted-* sources.md

## help: List available targets.
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'
