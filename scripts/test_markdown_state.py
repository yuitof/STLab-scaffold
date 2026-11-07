#!/usr/bin/env python3
"""Regression checks for Markdown state records and watcher ownership."""

import contextlib
import fcntl
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import markdown_state as state
import preview_markdown as preview


class MarkdownStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.folder = self.root / 'paper/markdown'
        self.folder.mkdir(parents=True)
        (self.root / 'temp').mkdir()
        self.write('cover.md', '# Cover\n')
        self.write('01.md', '# Objective\n\nOriginal.  \nNext line.\n\n')
        self.write('02.md', '# Theory\n')
        self.source = 'paper/markdown/01.md'
        for latex in [False, True]:
            record = {'version': 1, 'hashes': {}}
            if latex:
                record['snapshots'] = {}
            state.save_state(self.root, record, latex)

    def write(self, name, content):
        (self.folder / name).write_text(content, encoding='utf-8')

    def run_operation(self, command, files=None, force=False):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            with state.synchronized_preview(self.root):
                state.run_operation(self.root, command, files or [self.source], force)
        self.assertFalse(preview.watcher_running(self.root / 'temp'))
        return output.getvalue()

    def record_bytes(self):
        return tuple((self.root / name).read_bytes() for name in [state.READ_STATE, state.LATEX_STATE])

    def test_check_does_not_advance_records(self):
        before = self.record_bytes()
        output = json.loads(self.run_operation('check'))
        self.assertEqual(output['files'][0]['read_status'], 'new')
        self.assertEqual(output['files'][0]['latex_status'], 'new')
        self.assertEqual(self.record_bytes(), before)

    def test_read_records_only_read_history(self):
        latex_before = (self.root / state.LATEX_STATE).read_bytes()
        self.assertIn('Original.', self.run_operation('read'))
        reads = state.load_state(self.root)
        self.assertEqual(reads['hashes'][self.source], state.file_hash(self.root / self.source))
        self.assertEqual((self.root / state.LATEX_STATE).read_bytes(), latex_before)

    def test_unchanged_read_skips_content_and_writes(self):
        self.run_operation('read')
        path = self.root / state.READ_STATE
        before = path.stat().st_mtime_ns
        self.assertEqual(self.run_operation('read'), 'Unchanged: ' + self.source + '\n')
        self.assertEqual(path.stat().st_mtime_ns, before)

    def test_force_read_after_context_loss(self):
        self.run_operation('read')
        self.assertIn('Original.', self.run_operation('read', force=True))

    def test_record_rejects_unread_source(self):
        before = self.record_bytes()
        with self.assertRaisesRegex(state.StateError, 'Read this exact Markdown version'):
            self.run_operation('record-latex')
        self.assertEqual(self.record_bytes(), before)
        self.assertFalse((self.root / state.SNAPSHOTS).exists())

    def test_record_rejects_source_changed_after_read(self):
        self.run_operation('read')
        before = self.record_bytes()
        self.write('01.md', '# Changed during conversion\n')
        with self.assertRaises(state.StateError):
            self.run_operation('record-latex')
        self.assertEqual(self.record_bytes(), before)

    def test_record_copies_exact_bytes_and_preserves_tex(self):
        tex = self.root / 'paper/tex/sections/01.tex'
        tex.parent.mkdir(parents=True)
        tex.write_text('Independent LaTeX corrections.\n')
        self.run_operation('read')
        self.run_operation('record-latex')
        record = state.load_state(self.root, latex=True)
        snapshot = self.root / record['snapshots'][self.source]
        self.assertEqual(snapshot.read_bytes(), (self.root / self.source).read_bytes())
        self.assertEqual(tex.read_text(), 'Independent LaTeX corrections.\n')

    def test_unchanged_record_does_not_rewrite_snapshot_or_json(self):
        self.run_operation('read')
        self.run_operation('record-latex')
        record = state.load_state(self.root, latex=True)
        paths = [self.root / state.LATEX_STATE, self.root / record['snapshots'][self.source]]
        before = [path.stat().st_mtime_ns for path in paths]
        self.run_operation('record-latex')
        self.assertEqual([path.stat().st_mtime_ns for path in paths], before)

    def test_diff_uses_snapshot_without_advancing_history(self):
        self.run_operation('read')
        self.run_operation('record-latex')
        self.write('01.md', '# Objective\n\nUpdated.\n')
        before = self.record_bytes()
        output = self.run_operation('diff')
        self.assertIn('-Original.', output)
        self.assertIn('+Updated.', output)
        self.assertEqual(self.record_bytes(), before)

    def test_new_conversion_keeps_prior_immutable_snapshot(self):
        self.run_operation('read')
        self.run_operation('record-latex')
        before = state.load_state(self.root, latex=True)
        old_path = self.root / before['snapshots'][self.source]
        old_data = old_path.read_bytes()
        self.write('01.md', '# New version\n')
        self.run_operation('read')
        self.run_operation('record-latex')
        after = state.load_state(self.root, latex=True)
        self.assertNotEqual(before['snapshots'], after['snapshots'])
        self.assertEqual(old_path.read_bytes(), old_data)

    def test_diff_without_conversion_does_not_invent_baseline(self):
        before = self.record_bytes()
        self.assertIn('No LaTeX synchronization baseline', self.run_operation('diff'))
        self.assertEqual(self.record_bytes(), before)

    def test_corrupt_snapshot_is_not_used_or_overwritten(self):
        self.run_operation('read')
        self.run_operation('record-latex')
        record = state.load_state(self.root, latex=True)
        snapshot = self.root / record['snapshots'][self.source]
        snapshot.write_text('damaged')
        with self.assertRaisesRegex(state.StateError, 'snapshot is damaged'):
            self.run_operation('record-latex')
        self.assertEqual(snapshot.read_text(), 'damaged')

    def test_invalid_state_is_preserved(self):
        path = self.root / state.READ_STATE
        path.write_text('{bad JSON')
        with self.assertRaisesRegex(state.StateError, 'Invalid state'):
            self.run_operation('check')
        self.assertEqual(path.read_text(), '{bad JSON')

    def test_paths_in_old_or_outside_project_are_rejected(self):
        for name in ['(old)/hidden.md', '../outside.md', 'temp/snapshot.md']:
            with self.subTest(name=name), self.assertRaises(state.StateError):
                state.selected_files(self.root, [name])

    def test_changed_file_during_read_is_not_recorded(self):
        before = self.record_bytes()
        with mock.patch.object(state, 'captured_text', side_effect=state.StateError('changed')):
            with self.assertRaises(state.StateError):
                self.run_operation('read')
        self.assertEqual(self.record_bytes(), before)

    def test_exception_stops_owned_watcher(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'test failure'):
                with state.synchronized_preview(self.root):
                    self.assertTrue(preview.watcher_running(self.root / 'temp'))
                    raise RuntimeError('test failure')
        self.assertFalse(preview.watcher_running(self.root / 'temp'))

    def test_existing_watcher_is_left_running(self):
        program = Path(preview.__file__).resolve()
        with tempfile.TemporaryFile() as log:
            process = subprocess.Popen(
                [sys.executable, str(program), '--watch', '--source-dir', str(self.folder),
                 '--runtime-dir', str(self.root / 'temp')], stdout=log, stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 5
                while not preview.watcher_running(self.root / 'temp'):
                    self.assertIsNone(process.poll())
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.05)
                with contextlib.redirect_stderr(io.StringIO()):
                    with state.synchronized_preview(self.root):
                        self.assertIsNone(process.poll())
                self.assertIsNone(process.poll())
                self.assertTrue(preview.watcher_running(self.root / 'temp'))
            finally:
                process.terminate()
                process.wait(timeout=3)
        self.assertFalse(preview.watcher_running(self.root / 'temp'))

    def test_live_saved_edits_sync_both_directions(self):
        def wait_until(check):
            deadline = time.monotonic() + 3
            while not check():
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.05)

        with contextlib.redirect_stderr(io.StringIO()):
            with state.synchronized_preview(self.root):
                combined = self.folder / 'preview.md'
                self.write('01.md', '# Saved source edit\n')
                wait_until(lambda: '# Saved source edit' in combined.read_text())
                sections = preview.parse_preview(combined.read_text())
                sections['01.md'] = '# Saved preview edit\n'
                combined.write_text(preview.render(sections))
                wait_until(lambda: (self.root / self.source).read_text() == '# Saved preview edit\n')
        self.assertFalse(preview.watcher_running(self.root / 'temp'))

    def test_preview_error_prevents_comparison_and_stops_watcher(self):
        self.run_operation('read')
        (self.folder / 'preview.md').write_text('broken preview markers')
        before = self.record_bytes()
        with self.assertRaisesRegex(state.StateError, 'Preview synchronization failed'):
            self.run_operation('check')
        self.assertEqual(self.record_bytes(), before)
        self.assertFalse(preview.watcher_running(self.root / 'temp'))

    def test_review_refuses_pending_source_edits_without_applying_them(self):
        self.run_operation('read')
        self.write('01.md', '# Pending source edit\n')
        before = {path.name: path.read_bytes() for path in self.folder.glob('*.md')}
        records = self.record_bytes()
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(preview.SyncError):
                with state.synchronized_preview(self.root, review=True):
                    self.fail('Review should not proceed with pending synchronization.')
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.folder.glob('*.md')})
        self.assertEqual(records, self.record_bytes())
        self.assertFalse(preview.watcher_running(self.root / 'temp'))

    def test_review_refuses_pending_preview_edits_without_applying_them(self):
        self.run_operation('read')
        combined = self.folder / 'preview.md'
        sections = preview.parse_preview(combined.read_text())
        sections['01.md'] = '# Pending preview edit\n'
        combined.write_text(preview.render(sections))
        before = {path.name: path.read_bytes() for path in self.folder.glob('*.md')}
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(preview.SyncError):
                with state.synchronized_preview(self.root, review=True):
                    self.fail('Review should not apply pending preview edits.')
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.folder.glob('*.md')})
        self.assertFalse(preview.watcher_running(self.root / 'temp'))

    def test_review_uses_read_only_watcher_when_preview_matches(self):
        self.run_operation('read')
        before = {path.name: path.stat().st_mtime_ns for path in self.folder.glob('*.md')}
        with contextlib.redirect_stderr(io.StringIO()):
            with state.synchronized_preview(self.root, review=True):
                status = json.loads((self.root / 'temp/preview-watcher.json').read_text())
                self.assertTrue(status['read_only'])
        self.assertEqual(before, {path.name: path.stat().st_mtime_ns for path in self.folder.glob('*.md')})
        self.assertFalse(preview.watcher_running(self.root / 'temp'))

    def test_review_cli_can_record_reads_without_changing_report_sources(self):
        preview.update_preview(self.folder)
        before = {path.name: path.read_bytes() for path in self.folder.glob('*.md')}
        command = [sys.executable, str(Path(state.__file__).resolve()), '--project-root',
                   str(self.root), '--review', 'read', self.source]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(self.source, state.load_state(self.root)['hashes'])
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.folder.glob('*.md')})
        self.assertFalse(preview.watcher_running(self.root / 'temp'))

    def test_review_cli_rejects_advancing_conversion_history(self):
        command = [sys.executable, str(Path(state.__file__).resolve()), '--project-root',
                   str(self.root), '--review', 'record-latex', self.source]
        before = self.record_bytes()
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unavailable during a read-only review', result.stderr)
        self.assertEqual(before, self.record_bytes())
        self.assertFalse(preview.watcher_running(self.root / 'temp'))

    def test_cli_defaults_and_shutdown_notice(self):
        command = [sys.executable, str(Path(state.__file__).resolve()), '--project-root', str(self.root), 'check']
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([entry['path'] for entry in json.loads(result.stdout)['files']],
                         ['paper/markdown/cover.md', 'paper/markdown/01.md', 'paper/markdown/02.md'])
        self.assertIn('preview_markdown.py is not running now.', result.stderr)
        self.assertFalse(preview.watcher_running(self.root / 'temp'))

    def test_concurrent_state_command_is_rejected(self):
        command = [sys.executable, str(Path(state.__file__).resolve()), '--project-root', str(self.root), 'check']
        with (self.root / 'temp/markdown-state.lock').open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Another Markdown state command', result.stderr)
        self.assertFalse(preview.watcher_running(self.root / 'temp'))


if __name__ == '__main__':
    unittest.main()
