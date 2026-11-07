#!/usr/bin/env python3
"""Regression checks for bidirectional Markdown synchronization."""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import preview_markdown as sync


class PreviewSyncTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.write('cover.md', '# Cover\n')
        self.write('01.md', '# Objective\n')
        self.write('02.md', '# Theory\n')
        self.run_sync()

    def write(self, name, content):
        (self.folder / name).write_text(content, encoding='utf-8')

    def read(self, name):
        return (self.folder / name).read_text(encoding='utf-8')

    def run_sync(self):
        with contextlib.redirect_stdout(io.StringIO()):
            sync.update_preview(self.folder)

    def edit_preview(self, name, content):
        sections = sync.parse_preview(self.read('preview.md'))
        sections[name] = content
        self.write('preview.md', sync.render(sections))

    def snapshot(self):
        return {path.name: path.read_bytes() for path in self.folder.iterdir()}

    def test_cover_first_and_numbered_order(self):
        self.write('10.md', '# Ten\n')
        self.write('03.md', '# Three\n')
        self.run_sync()
        self.assertEqual(
            list(sync.parse_preview(self.read('preview.md'))),
            ['cover.md', '01.md', '02.md', '03.md', '10.md'],
        )

    def test_section_edit_updates_preview_without_rewriting_source(self):
        content = '# Objective\n\nPreserve a hard break.  \nNext line.\n\n'
        self.write('01.md', content)
        before = (self.folder / '01.md').stat().st_mtime_ns
        self.run_sync()
        self.assertEqual(sync.parse_preview(self.read('preview.md'))['01.md'], content)
        self.assertEqual((self.folder / '01.md').stat().st_mtime_ns, before)

    def test_preview_edit_updates_exact_source_and_survives_restart(self):
        content = '# Objective\n\nEdited in preview.  \nNext line.\n\n'
        self.edit_preview('01.md', content)
        self.run_sync()
        self.assertEqual(self.read('01.md'), content)
        before = self.snapshot()
        self.run_sync()
        self.assertEqual(self.snapshot(), before)

    def test_no_changes_do_not_rewrite_files(self):
        before = {p.name: p.stat().st_mtime_ns for p in self.folder.iterdir()}
        self.run_sync()
        self.assertEqual(before, {p.name: p.stat().st_mtime_ns for p in self.folder.iterdir()})

    def test_independent_edits_merge(self):
        self.write('01.md', '# Source edit\n')
        self.edit_preview('02.md', '# Preview edit\n')
        self.run_sync()
        self.assertEqual(self.read('01.md'), '# Source edit\n')
        self.assertEqual(self.read('02.md'), '# Preview edit\n')
        self.assertEqual(sync.parse_preview(self.read('preview.md'))['01.md'], '# Source edit\n')

    def test_conflicts_preserve_all_files_until_reconciled(self):
        self.write('01.md', '# Source edit\n')
        self.edit_preview('01.md', '# Preview edit\n')
        before = self.snapshot()
        with self.assertRaisesRegex(sync.SyncError, 'Conflicting edits in 01.md'):
            self.run_sync()
        self.assertEqual(self.snapshot(), before)
        self.write('01.md', '# Preview edit\n')
        self.run_sync()
        self.assertEqual(self.read('01.md'), '# Preview edit\n')

    def test_addition_and_deletion_of_sections(self):
        self.write('03.md', '# New section\n')
        self.run_sync()
        self.assertIn('03.md', sync.parse_preview(self.read('preview.md')))
        (self.folder / '03.md').unlink()
        self.run_sync()
        self.assertNotIn('03.md', sync.parse_preview(self.read('preview.md')))

    def test_deleted_section_with_preview_edit_is_a_conflict(self):
        (self.folder / '02.md').unlink()
        self.edit_preview('02.md', '# Keep this edit\n')
        before = self.snapshot()
        with self.assertRaisesRegex(sync.SyncError, 'Conflicting edits in 02.md'):
            self.run_sync()
        self.assertEqual(self.snapshot(), before)

    def test_damaged_markers_preserve_all_files(self):
        self.write('preview.md', self.read('preview.md').replace('END SOURCE: 01.md', 'END SOURCE: ../01.md'))
        before = self.snapshot()
        with self.assertRaisesRegex(sync.SyncError, 'Preview structure changed'):
            self.run_sync()
        self.assertEqual(self.snapshot(), before)

    def test_preview_block_deletion_is_rejected(self):
        sections = sync.parse_preview(self.read('preview.md'))
        del sections['02.md']
        self.write('preview.md', sync.render(sections))
        before = self.snapshot()
        with self.assertRaisesRegex(sync.SyncError, 'blocks were added or removed'):
            self.run_sync()
        self.assertEqual(self.snapshot(), before)

    def test_missing_state_never_overwrites_divergent_preview(self):
        (self.folder / sync.STATE_NAME).unlink()
        self.edit_preview('01.md', '# Unsynced edit\n')
        before = self.snapshot()
        with self.assertRaisesRegex(sync.SyncError, 'No sync history'):
            self.run_sync()
        self.assertEqual(self.snapshot(), before)

    def test_matching_preview_can_recreate_state(self):
        (self.folder / sync.STATE_NAME).unlink()
        self.run_sync()
        self.assertTrue((self.folder / sync.STATE_NAME).is_file())

    def test_missing_preview_is_recreated(self):
        (self.folder / 'preview.md').unlink()
        self.write('01.md', '# Current source\n')
        self.run_sync()
        self.assertEqual(sync.parse_preview(self.read('preview.md'))['01.md'], '# Current source\n')

    def test_duplicate_blocks_are_rejected(self):
        preview = self.read('preview.md')
        block = '<!-- BEGIN SOURCE: 01.md -->\nDuplicate\n<!-- END SOURCE: 01.md -->\n'
        self.write('preview.md', preview + block)
        before = self.snapshot()
        with self.assertRaisesRegex(sync.SyncError, 'Duplicate preview block'):
            self.run_sync()
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
