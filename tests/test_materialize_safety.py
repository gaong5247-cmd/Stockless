#!/usr/bin/env python3
"""Regression checks for disposable output paths and pinned source integrity."""
from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "stockless_materialize", Path(__file__).resolve().parents[1] / "tools/materialize.py"
)
assert SPEC is not None and SPEC.loader is not None
materializer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(materializer)


def mark_materialized(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / materializer.MATERIALIZED_MARKER).write_text(
        "Stockless: v0.9.0\n"
        f"Stockfish: {materializer.STOCKFISH_SHA}\n"
        f"Reckless reference: {materializer.RECKLESS_SHA}\n",
        encoding="utf-8",
    )


class OutputPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="stockless-output-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "repo"
        self.root.mkdir()
        self.sentinel = self.root / "source.txt"
        self.sentinel.write_text("keep the original source", encoding="utf-8")
        root_patch = patch.object(materializer, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def test_rejects_repository_and_ancestors_before_any_source_operations(self) -> None:
        for path in (self.root, self.base, self.root / "build" / ".."):
            with self.subTest(path=path), patch.object(materializer, "ensure_submodules") as ensure:
                with self.assertRaises(ValueError):
                    materializer.materialize(path)
                ensure.assert_not_called()
                self.assertEqual(self.sentinel.read_text(), "keep the original source")

    def test_rejects_source_directories_and_build_container(self) -> None:
        for name in (".git", ".github", "src", "tools", "tests", "docs",
                     "upstream", "upstream/stockfish", "build"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                materializer.validate_output_path(self.root / name)

    def test_accepts_new_build_directory(self) -> None:
        path = self.root / "build" / "stockless-src"
        self.assertEqual(materializer.validate_output_path(path), path)
        self.assertFalse(path.exists(), "Validation must not create output directories")

    def test_accepts_empty_build_directory(self) -> None:
        path = self.root / "build" / "custom-output"
        path.mkdir(parents=True)
        self.assertEqual(materializer.validate_output_path(path), path)

    def test_accepts_new_or_empty_external_directory(self) -> None:
        path = self.base / "external-output"
        self.assertEqual(materializer.validate_output_path(path), path)
        path.mkdir()
        self.assertEqual(materializer.validate_output_path(path), path)

    def test_accepts_previous_materialized_trees(self) -> None:
        for path in (self.root / "build" / "stockless-src", self.base / "external"):
            mark_materialized(path)
            (path / "generated-object.o").write_bytes(b"generated")
            with self.subTest(path=path):
                self.assertEqual(materializer.validate_output_path(path), path)

    def test_rejects_unrelated_nonempty_directories_without_removing_files(self) -> None:
        for path in (self.root / "build" / "unrelated", self.base / "unrelated"):
            path.mkdir(parents=True)
            valuable_file = path / "important.txt"
            valuable_file.write_text("do not delete", encoding="utf-8")
            with self.subTest(path=path), self.assertRaises(ValueError):
                materializer.validate_output_path(path)
            self.assertEqual(valuable_file.read_text(), "do not delete")

    def test_rejects_invalid_marker(self) -> None:
        path = self.base / "invalid-marker"
        path.mkdir()
        (path / materializer.MATERIALIZED_MARKER).write_text("unrelated file", encoding="utf-8")
        with self.assertRaises(ValueError):
            materializer.validate_output_path(path)

    def test_rejects_existing_file(self) -> None:
        path = self.base / "ordinary-file"
        path.write_text("keep", encoding="utf-8")
        with self.assertRaises(ValueError):
            materializer.validate_output_path(path)
        self.assertEqual(path.read_text(), "keep")

    def test_rejects_nested_git_repository_even_with_marker(self) -> None:
        path = self.base / "another-repository"
        mark_materialized(path)
        (path / ".git").mkdir()
        with self.assertRaises(ValueError):
            materializer.validate_output_path(path)

    def make_symlink(self, link: Path, target: Path, *, directory: bool = True) -> None:
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")

    def test_rejects_output_symlink_and_preserves_target(self) -> None:
        target = self.base / "real-output"
        mark_materialized(target)
        link = self.base / "linked-output"
        self.make_symlink(link, target)
        with self.assertRaises(ValueError):
            materializer.materialize(link)
        self.assertTrue(link.is_symlink())
        self.assertTrue((target / materializer.MATERIALIZED_MARKER).is_file())

    def test_resolves_parent_symlink_before_checking_protected_sources(self) -> None:
        link = self.base / "repository-alias"
        self.make_symlink(link, self.root)
        with self.assertRaises(ValueError):
            materializer.validate_output_path(link / "src")
        self.assertTrue(self.sentinel.is_file())

    def test_rejects_symlink_marker(self) -> None:
        path = self.base / "symlink-marker"
        path.mkdir()
        source = self.base / "valid-output"
        mark_materialized(source)
        self.make_symlink(path / materializer.MATERIALIZED_MARKER,
                          source / materializer.MATERIALIZED_MARKER, directory=False)
        with self.assertRaises(ValueError):
            materializer.validate_output_path(path)

    def test_failed_pin_check_preserves_existing_build(self) -> None:
        path = self.root / "build" / "stockless-src"
        mark_materialized(path)
        existing = path / "stockless"
        existing.write_bytes(b"previous build")
        with patch.object(materializer, "ensure_submodules"), \
                patch.object(materializer, "verify_pin", side_effect=RuntimeError("dirty source")):
            with self.assertRaisesRegex(RuntimeError, "dirty source"):
                materializer.materialize(path)
        self.assertEqual(existing.read_bytes(), b"previous build")


class PinnedSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="stockless-pin-test-")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Stockless test")
        self.git("config", "user.email", "stockless-test@example.invalid")
        self.source = self.repo / "tracked.cpp"
        self.source.write_text("original source\n", encoding="utf-8")
        (self.repo / ".gitignore").write_text("*.nnue\n*.o\nbuild/\n", encoding="utf-8")
        self.git("add", ".")
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", "test fixture")
        self.sha = self.git("rev-parse", "HEAD").strip()

    def git(self, *args: str) -> str:
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True)

    def test_accepts_exact_clean_pin(self) -> None:
        materializer.verify_pin(self.repo, self.sha, "Fixture")

    def test_rejects_different_pin(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "expected pinned"):
            materializer.verify_pin(self.repo, "0" * 40, "Fixture")

    def test_rejects_unstaged_tracked_source_change(self) -> None:
        self.source.write_text("modified source\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "modified tracked files"):
            materializer.verify_pin(self.repo, self.sha, "Fixture")

    def test_rejects_staged_tracked_source_change(self) -> None:
        self.source.write_text("modified source\n", encoding="utf-8")
        self.git("add", "tracked.cpp")
        with self.assertRaisesRegex(RuntimeError, "modified tracked files"):
            materializer.verify_pin(self.repo, self.sha, "Fixture")

    def test_rejects_staged_change_even_if_worktree_matches_head(self) -> None:
        self.source.write_text("staged source\n", encoding="utf-8")
        self.git("add", "tracked.cpp")
        self.source.write_text("original source\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "modified tracked files"):
            materializer.verify_pin(self.repo, self.sha, "Fixture")

    def test_rejects_deleted_tracked_source(self) -> None:
        self.source.unlink()
        with self.assertRaisesRegex(RuntimeError, "modified tracked files"):
            materializer.verify_pin(self.repo, self.sha, "Fixture")

    def test_rejects_staged_new_source(self) -> None:
        (self.repo / "new.cpp").write_text("new source", encoding="utf-8")
        self.git("add", "new.cpp")
        with self.assertRaisesRegex(RuntimeError, "modified tracked files"):
            materializer.verify_pin(self.repo, self.sha, "Fixture")

    def test_allows_untracked_and_ignored_build_or_network_files(self) -> None:
        (self.repo / "network.nnue").write_bytes(b"weights")
        (self.repo / "search.o").write_bytes(b"object")
        (self.repo / "build").mkdir()
        (self.repo / "build" / "stockfish").write_bytes(b"binary")
        (self.repo / "untracked-note.txt").write_text("local note", encoding="utf-8")
        materializer.verify_pin(self.repo, self.sha, "Fixture")


if __name__ == "__main__":
    unittest.main()
