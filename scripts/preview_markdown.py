#!/usr/bin/env python3
"""Synchronize report sections with an editable combined Markdown preview."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sys
import tempfile
import time


HEADER = (
    "<!-- Editable combined preview. Edit text inside the BEGIN/END SOURCE markers,\n"
    "or edit cover.md and the numbered section files directly. Keep the markers\n"
    "and separators intact. Run the Watch Markdown preview task to sync saved edits. -->\n\n"
)
STATE_NAME = ".preview-state.json"
SOURCE_NAME = re.compile(r"(?:cover|[0-9][0-9])\.md\Z")
BLOCK = re.compile(
    r"^<!-- BEGIN SOURCE: (cover\.md|[0-9][0-9]\.md) -->\n"
    r"(.*?)\n<!-- END SOURCE: \1 -->$",
    re.MULTILINE | re.DOTALL,
)


class SyncError(Exception):
    """An ambiguous edit must be resolved before synchronization can continue."""


def watcher_running(runtime_dir):
    """Use a process-owned lock, rather than trusting a possibly stale PID."""
    runtime_dir.mkdir(parents=True, exist_ok=True)
    with (runtime_dir / "preview-watcher.lock").open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        return False


def watch(source_dir, runtime_dir):
    """Publish readiness so state tools can request a synchronized preview."""
    runtime_dir.mkdir(parents=True, exist_ok=True)
    status_path = runtime_dir / "preview-watcher.json"
    request_path = runtime_dir / "preview-sync-request.json"
    with (runtime_dir / "preview-watcher.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SyncError("A preview watcher is already running in this project.")
        previous_status = None
        last_error = None
        ready = False
        original_handler = signal.getsignal(signal.SIGTERM)

        def stop(signum, frame):
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, stop)
        print("Watching Markdown drafts and preview; press Ctrl+C to stop.", flush=True)
        try:
            while True:
                status = {
                    "version": 1, "pid": os.getpid(),
                    "source_dir": str(source_dir.resolve()),
                    "status": "ready", "request_id": None,
                }
                try:
                    request = read_optional(request_path)
                    if request is not None:
                        status["request_id"] = json.loads(request)["request_id"]
                    update_preview(source_dir)
                    last_error = None
                except (OSError, UnicodeError, SyncError, ValueError, KeyError, TypeError) as error:
                    message = str(error)
                    status.update(status="error", message=message)
                    if message != last_error:
                        print("Sync deferred: " + message, file=sys.stderr, flush=True)
                        last_error = message
                serialized = json.dumps(status, indent=2) + "\n"
                if serialized != previous_status:
                    atomic_write(status_path, serialized)
                    previous_status = serialized
                if not ready:
                    print("Markdown preview watcher ready.", flush=True)
                    ready = True
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            signal.signal(signal.SIGTERM, original_handler)
            status_path.unlink(missing_ok=True)


def ordered(names):
    return sorted(names, key=lambda name: (name != "cover.md", name))


def digest(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def read_optional(path):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def atomic_write(path, content):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=".preview-", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        temporary.chmod(0o644)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def render(sections):
    blocks = [
        "<!-- BEGIN SOURCE: {0} -->\n{1}\n<!-- END SOURCE: {0} -->".format(
            name, sections[name]
        )
        for name in ordered(sections)
    ]
    return HEADER + "\n\n---\n\n".join(blocks) + "\n"


def parse_preview(content):
    sections = {}
    for match in BLOCK.finditer(content):
        name, body = match.groups()
        if name in sections:
            raise SyncError("Duplicate preview block: " + name)
        sections[name] = body
    if "cover.md" not in sections or render(sections) != content:
        raise SyncError(
            "Preview structure changed. Keep the header, separators, and BEGIN/END "
            "SOURCE markers intact; edit only the text inside each block."
        )
    return sections


def load_state(content):
    try:
        state = json.loads(content)
        if state["version"] != 1:
            raise ValueError("unsupported state version")
        hashes = state["hashes"]
        if not isinstance(hashes, dict) or "cover.md" not in hashes:
            raise ValueError("missing source hashes")
        if not all(
            SOURCE_NAME.fullmatch(name)
            and isinstance(value, str)
            and re.fullmatch(r"[0-9a-f]{64}", value)
            for name, value in hashes.items()
        ):
            raise ValueError("invalid source hashes")
        return hashes
    except (KeyError, TypeError, ValueError) as error:
        raise SyncError("Cannot read sync state: {}".format(error)) from error


def update_preview(folder):
    paths = [folder / "cover.md", *sorted(folder.glob("[0-9][0-9].md"))]
    raw_sources = {path.name: path.read_text(encoding="utf-8") for path in paths}
    sources = dict(raw_sources)
    output = folder / "preview.md"
    state_path = folder / STATE_NAME
    original_preview = read_optional(output)
    original_state = read_optional(state_path)
    preview = None

    if original_state is None:
        # Never guess which copy is newer when adopting an existing preview.
        if original_preview:
            preview = parse_preview(original_preview)
            if preview != sources:
                raise SyncError(
                    "No sync history and the preview differs from the section files. "
                    "Reconcile them before starting the watcher."
                )
        merged = sources
    else:
        base = load_state(original_state)
        if original_preview is not None:
            preview = parse_preview(original_preview)
            if set(preview) != set(base):
                raise SyncError(
                    "Preview blocks were added or removed. Create or delete numbered "
                    "section files directly; the watcher will update the blocks."
                )
        merged = {}
        conflicts = []
        for name in ordered(set(base) | set(sources)):
            source = sources.get(name)
            source_hash = digest(source) if source is not None else None
            previous_hash = base.get(name)
            edited = preview.get(name) if preview is not None else source
            edited_hash = digest(edited) if edited is not None else None
            source_changed = source_hash != previous_hash
            preview_changed = edited_hash != previous_hash
            if source_changed and preview_changed and source_hash != edited_hash:
                conflicts.append(name)
                continue
            chosen = edited if preview_changed else source
            if chosen is not None:
                merged[name] = chosen
        if conflicts:
            raise SyncError(
                "Conflicting edits in {}. Both copies were preserved. Make the "
                "section file and its preview block match to resume syncing.".format(
                    ", ".join(conflicts)
                )
            )

    # Defer if an editor saved another version while the files were being read.
    current_paths = {path.name for path in folder.glob("[0-9][0-9].md")}
    current_paths.add("cover.md")
    if current_paths != set(raw_sources) or any(
        read_optional(folder / name) != content for name, content in raw_sources.items()
    ) or read_optional(output) != original_preview or read_optional(state_path) != original_state:
        raise SyncError("Files changed during synchronization; retrying on the next pass.")

    source_updates = 0
    for name, content in merged.items():
        if sources.get(name) != content:
            atomic_write(folder / name, content)
            source_updates += 1
    combined = render(merged)
    if original_preview != combined:
        atomic_write(output, combined)
    state = json.dumps(
        {"version": 1, "hashes": {name: digest(merged[name]) for name in ordered(merged)}},
        indent=2,
    ) + "\n"
    if original_state != state:
        atomic_write(state_path, state)
    if source_updates or original_preview != combined:
        print(
            "Synchronized {} ({} sections; {} source files updated).".format(
                output.name, len(merged), source_updates
            ), flush=True,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true", help="Sync saved changes every 0.5 seconds.")
    parser.add_argument(
        "--source-dir", type=Path,
        default=Path(__file__).resolve().parent.parent / "paper" / "markdown",
        help="Directory containing cover.md and numbered section files.",
    )
    parser.add_argument(
        "--runtime-dir", type=Path,
        default=Path(__file__).resolve().parent.parent / "temp",
        help="Directory for local watcher status and locks.",
    )
    args = parser.parse_args()
    if not args.watch:
        try:
            update_preview(args.source_dir)
        except (OSError, UnicodeError, SyncError) as error:
            parser.exit(1, "Sync deferred: {}\n".format(error))
        return

    try:
        watch(args.source_dir, args.runtime_dir)
    except (OSError, SyncError) as error:
        parser.exit(1, "Watcher unavailable: {}\n".format(error))


if __name__ == "__main__":
    main()
