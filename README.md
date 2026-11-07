# Lab report template

The reusable Markdown templates use English labels and headings. The TeX
templates retain their original Japanese text and layout.
For each new report project, copy its `data/cover_info.example.yaml` to
`data/cover_info.yaml` and fill in the project settings. Preserve that file when
continuing the same report or preparing a resubmission. The template tracks
the example rather than the project-specific copy.

## Editable Markdown preview

The watcher starts only when requested. Opening the folder does not start it.
When writing a report in VS Code, use
**Terminal > Run Task > Watch Markdown preview** to start syncing.
When finished, use **Terminal > Terminate Task > Watch Markdown preview** to stop
it. Leave it stopped when you are not writing a report.

Open `paper/markdown/preview.md` and press **Command+Shift+V** on macOS to view
the rendered Markdown. Open the file in the text editor to edit the combined
report. Saved changes sync in either direction within about one second:

- Edit `cover.md` or a numbered section file to update the combined preview.
- Edit text inside a `BEGIN SOURCE` / `END SOURCE` block in `preview.md` to
  update the corresponding source file. Keep the header, markers, and separators
  intact. The rendered Markdown view itself is read-only.
- Create or delete numbered section files (`01.md` through `99.md`) to change
  the sections included in the preview. The cover always appears first.

Changes to different sections can be merged. If both copies of the same section
change differently before a sync, the watcher reports a conflict and leaves both
copies untouched. Make the section file and its preview block match to resume.
Malformed markers also pause syncing until they are restored. Check the task
terminal for these messages.

The ignored `.preview-state.json` file stores synchronization hashes. Keep it
locally so the watcher can recognize edits after restarting. With no sync history,
an existing preview must match the source files before syncing can begin.

To run a single synchronization or start the watcher outside VS Code:

```sh
/usr/bin/python3 scripts/preview_markdown.py
/usr/bin/python3 scripts/preview_markdown.py --watch
```

The first command syncs once and exits. The second runs in the foreground until
you press **Ctrl+C**. Do not launch detached watchers with `nohup`, `&`, or a
separate background session.

## Markdown hashes and LaTeX snapshots

Use the state tool from the project root:

```sh
/usr/bin/python3 scripts/markdown_state.py check
/usr/bin/python3 scripts/markdown_state.py read paper/markdown/01.md
/usr/bin/python3 scripts/markdown_state.py diff paper/markdown/01.md
```

`check` reports whether files changed since their last read and last LaTeX update,
without advancing either record. `read` displays changed files and records their
hashes; use `read --force FILE` if the earlier content is no longer in context.
`diff` shows Markdown edits relative to the last synchronized snapshot. Omit file
arguments to process the report's cover and numbered sections. Explicit paths can
select other Markdown, including `AGENTS.md` and textbook transcriptions.

After applying the exact Markdown version you read to LaTeX, record it:

```sh
/usr/bin/python3 scripts/markdown_state.py record-latex paper/markdown/01.md
```

This command copies the Markdown and records its hash. It refuses a version that
has not been read or has changed since reading. It does not convert or edit LaTeX.
Use it only after a completed conversion or synchronization. Changes to LaTeX
alone do not update Markdown or either hash record.

The tracked records are `temp/markdown-read-state.json` and
`temp/markdown-latex-state.json`. Immutable snapshots live under
`temp/markdown-latex-snapshots/<SHA-256>/<project-relative-source-path>`; earlier
versions remain available. Unchanged records and snapshots are not rewritten.

Every command waits for a successfully synchronized preview before comparing
hashes. It starts a temporary foreground watcher if needed, stops that watcher
on completion or error, and reports its shutdown. A pre-existing watcher is left
running. Watcher locks and status files also live under `temp/` and stay local.

Run the regression checks after changing either tool:

```sh
/usr/bin/python3 scripts/test_preview_markdown.py
/usr/bin/python3 scripts/test_markdown_state.py
```

Empty folders contain `.gitkeep` placeholders so Git can track them. Codex ignores
these placeholders when working with project content.

## License

Original contributions are licensed under the [MIT License](LICENSE).
The university-provided template and copied or adapted portions of it are outside
that license's scope and remain subject to the original provider's terms.
