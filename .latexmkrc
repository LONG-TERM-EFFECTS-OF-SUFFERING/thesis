# Engine: pdflatex (project relies on inputenc/fontenc/lmodern + minted).
$pdf_mode = 1;

# Build artifacts go into ./build to keep the repo root clean.
$out_dir = 'build';
$aux_dir = 'build';

# pdflatex flags:
#   -shell-escape       : required by minted
#   -halt-on-error      : fail fast in CI
#   -file-line-error    : clickable errors in editors
#   -interaction=nonstopmode : no interactive prompts
$pdflatex = 'pdflatex -shell-escape -halt-on-error -file-line-error '
          . '-interaction=nonstopmode %O %S';

# Bibliography: biber (project uses biblatex with backend=biber).
$bibtex_use = 2;
$biber = 'biber --validate-datamodel %O %S';

# Tell latexmk that minted writes a _minted-<jobname> directory; clean it on -C.
$clean_ext = '_minted-%R nav snm vrb run.xml bbl bcf';

# Always re-run if cross-references change (handles cleveref edge cases).
$max_repeat = 5;

# Default top-level file.
@default_files = ('main.tex');
