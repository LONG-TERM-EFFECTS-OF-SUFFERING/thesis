# Web application for automated collection, analysis and visualization of YouTube data

## Abstract

YouTube, with 2,530 million monthly users, serves as a primary news source for 35% of U.S. adults. However, current YouTube analysis tools rely on proprietary, black-box methodologies that limit transparency and reproducibility, creating barriers for academic research requiring verifiable systems.

This thesis proposes to develop a web application to **process**, **analyze** and **visualize** YouTube data using transparent and reproducible methods. The system comprises three integrated components: a data collection module using the YouTube Data API with natural language processing for query translation, a data processing pipeline for cleaning and normalizing responses and an interactive visualization layer.

The methodology follows an adapted Scrum framework with iterative two-week sprints. Development includes technology stack selection, system architecture design, API integration with LLM-powered interfaces, database implementation and comprehensive testing. All services are containerized using Docker for reproducible deployment.

The resulting application will provide a no-cost, transparent alternative to commercial tools, democratizing YouTube data analysis for academic researchers, non-profits and independent investigators. By providing fully documented methodology and open architecture, this work promotes **reproducible science** and serves as a **foundational tool** for research in social media analysis, polarization and information dissemination.

## Template

This thesis was written using a custom [LaTeX template](https://github.com/braz9LKDI/professional_project_thesis_template) designed for **professional projects** (thesis work format) for the Systems engineer program at the Universidad del Valle.

## Tooling

This thesis uses my own [`style_config`](https://github.com/braz9LKDI/style_config) kit to keep the LaTeX source consistent, specifically its `latex/` stack:

- latexindent handles formatting: indentation, line breaks around environments and alignment of tabular and math delimiters.

- chktex catches common LaTeX issues like spacing problems, bad command usage and quoting mistakes.

- latexmk orchestrates the build, running pdflatex and biber the right number of times until cross-references stabilize.

- EditorConfig sets editor-level basics: indent style, line endings and final newline.

Every config in the root of this repository (`.latexindent.yaml`, `.chktexrc`, `.latexmkrc`, `.editorconfig`, `.vscode/`) is a direct copy from that stack. The same setup can be adopted in any LaTeX project by copying the `latex/` folder and following its README.
