# Lab report template

The reusable Markdown templates use English labels and headings. The TeX
templates retain their original Japanese text and layout.
Copy `data/cover_info.example.yaml` to `data/cover_info.yaml` when starting a report.

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

Empty folders contain `.gitkeep` placeholders so Git can track them. Codex ignores
these placeholders when working with project content.
