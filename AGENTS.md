# Codex Instructions

## General Rules

- Keep the reusable Markdown template, tooling comments, and preview messages in English. Preserve existing TeX templates, including their original Japanese text, unless explicitly asked to edit them. Use the language required by the assignment when writing an actual report.
- For actual reports written in Japanese, use full-width commas and periods in Japanese prose.
- You may update this file when you identify useful general rules. Do not add information specific to an individual experiment or report.

## Folder Exclusions

- When a file or folder is clearly unnecessary, you may move it into an `(old)` folder in its parent directory. Create that `(old)` folder if needed. Archive items instead of deleting them; if their purpose is uncertain, ask before moving them.
- Ignore every folder named `(old)` anywhere in this project.
- Do not search, read, analyze, modify, or reference files inside these folders. Exclude them from recursive searches and file discovery.
- You may place archived items into `(old)` as described above, without inspecting its existing contents or overwriting existing items. Otherwise, access these folders only when I explicitly request it.

## Empty Folder Placeholders

- Keep an empty `.gitkeep` file in each otherwise empty project folder so Git can track the folder.
- Treat folders containing only ignored operating-system metadata, such as `.DS_Store`, as empty when adding placeholders.
- Codex must ignore `.gitkeep` files when searching, reading, analyzing, and processing project content. They are structural placeholders, not report sources or preview inputs.
- Do not add `.gitkeep` files to `.gitignore`; they must remain available for Git to track.

## Project Git Repository

- Each project uses its own Git repository. Initialization and project work may proceed before a parent repository starts tracking the project. Run `git init` only when the project has no existing or temporarily relocated Git metadata.
- Before the parent runs `git add` or `git commit` on the project while its local `.git` is present, verify that the parent already tracks the project's files as ordinary files. The parent must retain tracking of files excluded only by the project's `.git/info/exclude`; do not replace the project with a submodule or gitlink.
- If the parent has not started tracking the project, temporarily move its `.git` to `temp/.git` when preparing the initial parent `git add`, without overwriting an existing backup. Stage the project's ordinary files in the parent while keeping the parked metadata out of its index. Once the parent tracks those files, restore `.git`; subsequent parent add and commit operations may proceed with it present. Do not initialize another repository while its metadata is parked. Preserve existing worktree metadata when `.git` is a file.
- Keep a tracked copy of the exclude rules at `.git-exclude` in the project root. Copy it to `.git/info/exclude` after initialization or cloning, and keep both copies identical. For worktrees, locate the active exclude file with `git rev-parse --git-path info/exclude`.
- Use an allowlist for the documented project files, `.gitkeep` files, and their parent directories. Keep `(old)` folders, generated files, and other unlisted files excluded. Include `.git-exclude` itself in the allowlist.
- When the project structure changes, update the diagram below and both exclude-rule copies as needed. Verify that intended files are included and generated or archived files remain excluded.
- Use `temp/` for temporary files and folders. Track only its `.gitkeep` placeholder in the project repository.

## Project Structure

```text
.
├── .git-exclude
├── .gitignore
├── .vscode
│   ├── settings.json
│   └── tasks.json
├── AGENTS.md
├── README.md
├── data
│   └── cover_info.example.yaml
├── docs
│   ├── instructions
│   ├── references
│   │   └── textbooks
│   │       └── assests
│   └── templates
│       └── template.tex
├── paper
│   ├── markdown
│   │   ├── 01.md … 07.md
│   │   ├── cover.md
│   │   └── preview.md
│   ├── submission
│   └── tex
│       ├── paper.tex
│       └── sections
│           ├── 01.tex … 07.tex
│           └── cover.tex
├── scripts
│   ├── preview_markdown.py
│   └── test_preview_markdown.py
└── temp
```

Generated TeX build files, local synchronization state, Python caches, operating-system metadata, and `.gitkeep` placeholders are omitted from this overview. When starting a report, copy `data/cover_info.example.yaml` to `data/cover_info.yaml` and fill in the report's cover information.

| Location | Purpose |
| --- | --- |
| `.git-exclude` | Tracked copy of the local `.git/info/exclude` rules. |
| `.vscode/` | Editor settings and the manually started Markdown preview task. |
| `data/` | Raw experimental data and cover information. |
| `docs/instructions/` | Report requirements and detailed task instructions. |
| `docs/references/` | Documents and textbook materials provided in lectures. |
| `docs/templates/` | Report templates provided in lectures. |
| `paper/markdown/` | Editable Markdown drafts, with a separate file for each section and the cover. |
| `paper/tex/` | LaTeX sources, with `paper.tex` importing the cover and section files. |
| `paper/submission/` | Copies of compiled PDFs named for submission. |
| `scripts/` | Reusable project tools and their regression tests. Keep automation here, separate from report sources and experimental data. |
| `temp/` | Temporary files and folders, including temporarily relocated Git metadata when needed. Only `.gitkeep` is tracked by the project repository. |

### Scripts

| Script | Purpose |
| --- | --- |
| `scripts/preview_markdown.py` | Two-way Markdown preview synchronization; runs once by default or continuously with `--watch`. |
| `scripts/test_preview_markdown.py` | Regression tests for the preview tool; run after changing it. |

## Report Workflow

1. Read the relevant instructions in `docs/instructions/` and consult the templates in `docs/templates/` before drafting.
2. Create the report in Markdown first, under `paper/markdown/`. Keep each section in a separate file so it is easy to edit. I will provide most of the content in Markdown.
3. Use `docs/references/` to determine the required content, terminology, and level of detail.
4. Convert Markdown to LaTeX only when I explicitly ask. Consult the LaTeX template again when converting, and place the sources under `paper/tex/`.

## Draft Preservation and Confirmation Reviews

- Preserve the wording of Markdown drafts. They record my starting point, and I may return to them later. Do not rewrite, polish, normalize punctuation, or otherwise edit them unless I explicitly request those changes.
- Confirmation and pre-submission reviews are read-only by default. Do not change wording in Markdown, TeX, or other report sources as part of checking them. A request to check compliance does not authorize corrections or rewriting.
- If you find a mistake, error, ambiguity, or unmet requirement, report its location, explain the issue, and propose a correction before changing anything. Wait for my approval of that correction before applying it.
- When converting Markdown to TeX, preserve the draft's wording and make only the formatting changes needed for typesetting. Apply any correction or wording change only when I have explicitly approved it, and keep the original Markdown draft unless I separately ask to update it.
- Markdown line breaks do not have to be reproduced in LaTeX. Treat ordinary line breaks as drafting choices and arrange prose paragraphs and line wrapping for readability in the typeset report while preserving the wording. Retain breaks needed for mathematical alignment, code, lists, or other meaningful structure.
- After an approved correction, rerun the relevant checks and report the result. If approval is pending, leave the issue open in the confirmation record rather than silently fixing it or marking the report fully checked.

## DOCX Template Instructions

- Each class provides a DOCX report template. Look for it under `docs/templates/` and in other provided materials, respecting the folder exclusions. If the corresponding template cannot be found, ask me to provide it.
- The template's blue text explains what the report must include. Inspect the text colors as well as the content; a plain-text extraction alone cannot identify these instructions reliably. If the blue guidance cannot be found or read, ask me for it rather than assuming there are no requirements.
- Before drafting and again before submission, turn the blue instructions into a checklist and verify that the report satisfies every applicable item. Check the actual submission PDF as well as the sources, including any required sections, explanations, calculations, figures, and length limits.
- Keep the instructional blue text out of the submitted report unless the template explicitly asks for it. Report any unmet requirements, obtain my approval before corrections, and recheck the final PDF after approved changes before marking it ready for submission.

## Textbook References

- Each project has a corresponding textbook. Store textbook materials under `docs/references/textbooks/`. Look there and in other provided project materials, respecting the folder exclusions. If the textbook cannot be found, ask me to provide it.
- Before using information from the textbook, create a searchable Markdown transcription alongside the source material at `docs/references/textbooks/textbook.md`. If a transcription already exists, check its coverage and accuracy against the original and reuse it.
- Transcribe the supplied text faithfully, including headings, equations, tables, figure captions, exercises, and footnotes. Preserve page and item numbers so passages can be traced back to the original. Retain the source files and include image links or clearly marked descriptions for diagrams.
- Store images extracted from the textbook in `docs/references/textbooks/assests/`, beside `textbook.md`, and use relative Markdown links such as `![Figure description](assests/page-01-figure-01.png)`. Preserve their original captions and page references, and retain the original textbook files.
- Mark unreadable or uncertain passages explicitly instead of guessing, and distinguish any explanatory additions from the textbook text.
- Use the verified Markdown transcription for subsequent reference and return to the original when needed to resolve ambiguity. Extend the transcription when additional textbook pages are provided so it remains reusable.

## Bibliography

- Do not include university-provided course materials, such as textbooks, experiment manuals, report instructions, or templates, in the bibliography.
- Do not assign bibliography numbers to these materials in the report body. When needed, identify them in prose without a numbered citation.
- List only external literature actually consulted in the bibliography. Keep experimental-data provenance in the report body or analysis records instead of treating the experiment's own records as bibliography entries.
- After removing or changing bibliography entries, update the corresponding citations in Markdown and TeX and regenerate the submission PDF.

## Equations, Figures, and Tables

- Number every displayed equation consecutively throughout the report. Use LaTeX's automatic equation counters and add a unique `\label` for references. Inline expressions do not need equation numbers.
- In multiline derivations, number each complete equation or transformation step. Continuation lines belonging to the same expression share its number. Preserve page breaks where long derivations require them.
- Give every figure and every table in the report body a descriptive title in the report language and an automatically assigned number. Add a unique `\label` and use `\ref` or `\eqref` for references instead of typing reference numbers manually.
- Place figure captions below the figures and table captions above the tables. When several images are presented together, identify each image with its own numbered caption or a titled, lettered panel under a numbered figure.
- Check the compiled PDF for missing, duplicated, or overlapping numbers and captions. The cover's information fields are form layout, not numbered report tables.

## Markdown Preview

- The existing tool syncs saved edits between `paper/markdown/preview.md` and the separate cover and section files. The preview shows the cover first, then numbered sections in order.
- Edit section files directly or edit text inside the preview's BEGIN/END SOURCE markers. Keep its header, markers, and separators intact. Add or delete sections through the separate files.
- Start the watcher manually only while writing a report, and stop it when finished. Do not enable automatic startup or launch detached watchers. See `README.md` for VS Code and terminal commands.
- Keep the local `.preview-state.json` sync history. If a conflict occurs, preserve both versions and resolve it explicitly; never overwrite either version automatically.
- After changing the tool, run its regression tests and verify saved edits sync in both directions. Stop any test watcher afterward.

## Cover Information

### Sources

- Use `data/cover_info.yaml` as the source of cover information, including my personal information.
- If no lab partners are listed in the provided materials, treat the experiment as performed alone. Record an empty list in `lab_partners` and leave the lab-partner field on the cover blank.
- Find the experiment title in `docs/`, usually in a DOCX file under `docs/templates/`.
- Temperature, humidity, and atmospheric pressure measurements may be provided in `data/cover_info.yaml`, but are optional. Check that file first, then other files in `data/` as needed. If a measurement is absent, it may be omitted because it is unnecessary for that experiment.
- Record reusable cover information in `data/cover_info.yaml` to avoid looking it up repeatedly.

### Dates

- Use Japan Standard Time (JST, UTC+09:00) for all date and time calculations and cover timestamps.
- Do not display timezone labels such as `JST` or `UTC+09:00` on the cover or alongside report timestamps.
- Determine the experiment date as the most recent Friday relative to the current date in JST. The experiment session is in the morning.
- For an initial submission, set the submission date and time to the compilation date and time in JST, and leave the resubmission date blank.
- For a resubmission, preserve both the experiment date and the original submission date and time. Update the resubmission date and time to the compilation date and time in JST.

## Compilation and Submission

- Every time the project is compiled, create a copy of the resulting PDF under `paper/submission/`.
- Name that copy according to the filename rules below. Find the experiment number in `docs/` and the reporter's name in `data/cover_info.yaml`.

### PDF Requirements

- Submit one PDF containing the entire report, including the cover. Turnitin accepts only one file per submission.
- Use A4 pages with a single-column layout.
- Use the template supplied for the relevant experiment or module, or reproduce the same layout. Always include the cover.
- Include machine-readable text. Scanned handwritten reports are not accepted, and Turnitin rejects reports without text information.
- Keep the file size at or below 20 MB in principle.

### Submission Filename

- Use the experiment number in half-width characters followed immediately by the reporter's name in kanji: `<experiment_number><name_in_kanji>.pdf`.
- Example: `A-2<name_in_kanji>.pdf`, where `A-2` is the experiment number.
- For a revised report, append an uppercase half-width `R` before `.pdf`: `A-2<name_in_kanji>R.pdf`.

### Turnitin Submissions

- The submission page permits repeated uploads before the deadline. Each upload overwrites the previous submission.

## Checks Before Submission

- Verify every equation and calculation in the report. Write and run code to confirm the calculations and numerical results.
- Match the equation notation and formatting used in `docs/references/` where applicable.
- Confirm that the report includes everything required by the instructions in `docs/`. Inspect images when needed to verify those requirements.
- Flag unnatural wording or terminology that differs from the supplied materials under `docs/`, and propose corrections for my approval. Do not rewrite the report during the confirmation process.
- Confirm that the submission PDF and its filename comply with the Compilation and Submission rules above.
