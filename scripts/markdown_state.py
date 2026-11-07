#!/usr/bin/env python3
"""Check Markdown hashes, read changed drafts, and record completed LaTeX updates."""

import argparse
from contextlib import contextmanager
import difflib
import fcntl
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import time
import uuid

import preview_markdown as preview


READ_STATE = Path('temp/markdown-read-state.json')
LATEX_STATE = Path('temp/markdown-latex-state.json')
SNAPSHOTS = Path('temp/markdown-latex-snapshots')
FORBIDDEN = {'(old)', '.git', '.venv', '__pycache__'}


class StateError(Exception):
    """An operation cannot safely use the available state."""


def file_hash(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def valid_key(key):
    if not isinstance(key, str):
        return False
    path = PurePosixPath(key)
    return (
        not path.is_absolute() and path.as_posix() == key
        and not set(path.parts) & (FORBIDDEN | {'..'})
        and path.parts and path.parts[0] != 'temp'
        and path.suffix.lower() == '.md'
    )


def checked_path(root, relative):
    path = root / relative
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise StateError('Path leaves the project: ' + str(relative)) from error
    return path


def snapshot_name(key, digest):
    return (SNAPSHOTS / digest / key).as_posix()


def load_state(root, latex=False):
    path = root / (LATEX_STATE if latex else READ_STATE)
    empty = {'version': 1, 'hashes': {}}
    if latex:
        empty['snapshots'] = {}
    if not path.exists():
        return empty
    try:
        state = json.loads(path.read_text(encoding='utf-8'))
        hashes = state['hashes']
        if state['version'] != 1 or not isinstance(hashes, dict):
            raise ValueError('unsupported schema')
        if not all(valid_key(key) and isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value)
                   for key, value in hashes.items()):
            raise ValueError('invalid Markdown paths or hashes')
        if latex:
            snapshots = state['snapshots']
            if not isinstance(snapshots, dict) or set(snapshots) != set(hashes):
                raise ValueError('snapshot entries do not match hashes')
            if any(snapshots[key] != snapshot_name(key, value) for key, value in hashes.items()):
                raise ValueError('invalid snapshot path')
        return state
    except (KeyError, TypeError, ValueError) as error:
        raise StateError('Invalid state in {}: {}'.format(path.name, error)) from error


def write_bytes(path, content):
    if path.exists() and path.read_bytes() == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.markdown-state-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        temporary.chmod(0o644)
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def save_state(root, state, latex=False):
    content = (json.dumps(state, indent=2, sort_keys=True) + '\n').encode('utf-8')
    write_bytes(root / (LATEX_STATE if latex else READ_STATE), content)


def selected_files(root, arguments):
    if not arguments:
        folder = root / 'paper/markdown'
        paths = [folder / 'cover.md', *sorted(folder.glob('[0-9][0-9].md'))]
    else:
        paths = [Path(name) if Path(name).is_absolute() else root / name for name in arguments]
    selected = {}
    for path in paths:
        # Reject excluded paths before resolving symlinks or opening files.
        if set(path.parts) & FORBIDDEN:
            raise StateError('Excluded Markdown path: ' + str(path))
        try:
            key = path.resolve().relative_to(root).as_posix()
        except ValueError as error:
            raise StateError('Markdown path leaves the project: ' + str(path)) from error
        if not valid_key(key):
            raise StateError('Select source Markdown outside temp/: ' + key)
        selected[key] = checked_path(root, key)
    return selected


def captured_text(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise StateError('Markdown changed during the operation; retry: ' + str(path))
    return data, data.decode('utf-8')


@contextmanager
def synchronized_preview(root, timeout=8):
    """Borrow an existing watcher or start a bounded, non-detached child."""
    runtime = root / 'temp'
    runtime.mkdir(parents=True, exist_ok=True)
    process = None
    borrowed = False
    with tempfile.TemporaryFile(mode='w+t') as log:
        try:
            borrowed = preview.watcher_running(runtime)
            if not borrowed:
                program = Path(__file__).resolve().with_name('preview_markdown.py')
                process = subprocess.Popen(
                    [sys.executable, str(program), '--watch',
                     '--source-dir', str(root / 'paper/markdown'),
                     '--runtime-dir', str(runtime)],
                    cwd=str(root), stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT,
                )
            request_id = uuid.uuid4().hex
            preview.atomic_write(
                runtime / 'preview-sync-request.json',
                json.dumps({'version': 1, 'request_id': request_id}) + '\n',
            )
            deadline = time.monotonic() + timeout
            while True:
                if process is not None and process.poll() is not None:
                    log.seek(0)
                    raise StateError('Preview watcher exited: ' + log.read().strip())
                try:
                    status = json.loads((runtime / 'preview-watcher.json').read_text())
                except (FileNotFoundError, ValueError):
                    status = {}
                if status.get('request_id') == request_id:
                    if status.get('source_dir') != str((root / 'paper/markdown').resolve()):
                        raise StateError('The running watcher belongs to a different source directory.')
                    if status.get('status') != 'ready':
                        raise StateError('Preview synchronization failed: ' + status.get('message', 'unknown error'))
                    if not preview.watcher_running(runtime):
                        raise StateError('Preview watcher stopped before the hash comparison.')
                    break
                if time.monotonic() >= deadline:
                    raise StateError('Timed out waiting for a successfully synchronized preview.')
                time.sleep(0.05)
            yield
        finally:
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=3)
                if preview.watcher_running(runtime):
                    print('Temporary watcher stopped; another preview watcher is running.', file=sys.stderr)
                else:
                    print('preview_markdown.py is not running now.', file=sys.stderr)
            elif borrowed:
                running = preview.watcher_running(runtime)
                print('Pre-existing preview watcher {}.'.format('left running' if running else 'has stopped'), file=sys.stderr)
            else:
                print('No temporary preview watcher was started.', file=sys.stderr)


def run_operation(root, command, arguments, force=False):
    files = selected_files(root, arguments)
    reads = load_state(root)
    latex = load_state(root, latex=True)
    hashes = {key: file_hash(path) for key, path in files.items()}

    if command == 'check':
        def status(previous, current):
            return 'new' if previous is None else 'unchanged' if previous == current else 'changed'
        rows = [
            {'path': key, 'sha256': value,
             'read_status': status(reads['hashes'].get(key), value),
             'latex_status': status(latex['hashes'].get(key), value)}
            for key, value in hashes.items()
        ]
        print(json.dumps({'files': rows}, indent=2))
        return

    if command == 'read':
        updates = {}
        for key, path in files.items():
            if not force and reads['hashes'].get(key) == hashes[key]:
                print('Unchanged: ' + key)
                continue
            _, text = captured_text(path, hashes[key])
            print('--- {} (SHA-256: {}) ---'.format(key, hashes[key]))
            sys.stdout.write(text)
            if not text.endswith('\n'):
                print()
            updates[key] = hashes[key]
        # Do not claim a successful read if displaying the content fails.
        sys.stdout.flush()
        if updates:
            reads['hashes'].update(updates)
            save_state(root, reads)
        return

    if command == 'diff':
        for key, path in files.items():
            previous = latex['hashes'].get(key)
            if previous is None:
                print('No LaTeX synchronization baseline: ' + key)
            elif previous == hashes[key]:
                print('Unchanged since LaTeX synchronization: ' + key)
            else:
                baseline = checked_path(root, latex['snapshots'][key])
                _, before = captured_text(baseline, previous)
                _, after = captured_text(path, hashes[key])
                changes = ''.join(difflib.unified_diff(
                    before.splitlines(keepends=True), after.splitlines(keepends=True),
                    fromfile='last-synchronized/' + key, tofile=key,
                ))
                sys.stdout.write(changes)
                if changes and not changes.endswith('\n'):
                    print()
        return

    # Only an explicit record-latex command advances the conversion history.
    captured = {}
    for key, path in files.items():
        if reads['hashes'].get(key) != hashes[key]:
            raise StateError('Read this exact Markdown version before recording its LaTeX update: ' + key)
        captured[key] = captured_text(path, hashes[key])[0]
    for key, data in captured.items():
        name = snapshot_name(key, hashes[key])
        path = checked_path(root, name)
        if path.exists() and file_hash(path) != hashes[key]:
            raise StateError('Stored snapshot is damaged: ' + name)
        write_bytes(path, data)
        latex['hashes'][key] = hashes[key]
        latex['snapshots'][key] = name
    save_state(root, latex, latex=True)
    print('Recorded completed LaTeX updates for {} Markdown files.'.format(len(files)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parent.parent)
    commands = parser.add_subparsers(dest='command', required=True)
    for name, help_text in [
        ('check', 'Report read and LaTeX hash status without advancing either record.'),
        ('read', 'Display changed Markdown and record successful reads.'),
        ('diff', 'Show Markdown changes since its last completed LaTeX update.'),
        ('record-latex', 'Copy snapshots and record hashes AFTER completing a LaTeX update.'),
    ]:
        command = commands.add_parser(name, help=help_text)
        command.add_argument('files', nargs='*', help='Project-relative .md paths; default: report cover and sections.')
        if name == 'read':
            command.add_argument('--force', action='store_true', help='Read even unchanged content after context loss.')
    args = parser.parse_args()
    root = args.project_root.resolve()
    runtime = root / 'temp'
    runtime.mkdir(parents=True, exist_ok=True)
    try:
        with (runtime / 'markdown-state.lock').open('a+') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise StateError('Another Markdown state command is running; retry shortly.') from error
            with synchronized_preview(root):
                run_operation(root, args.command, args.files, getattr(args, 'force', False))
    except (OSError, UnicodeError, StateError, preview.SyncError) as error:
        parser.exit(1, 'Markdown state operation failed: {}\n'.format(error))


if __name__ == '__main__':
    main()
