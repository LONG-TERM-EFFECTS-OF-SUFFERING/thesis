$pdf_mode = 1;

$out_dir = 'build';
$aux_dir = 'build';

$pdflatex = 'pdflatex -shell-escape -halt-on-error -file-line-error '
          . '-interaction=nonstopmode %O %S';

$bibtex_use = 2;
$biber = 'biber --validate-datamodel %O %S';

$clean_ext = '_minted-%R nav snm vrb run.xml bbl bcf';

$max_repeat = 5;

@default_files = ('main.tex');
