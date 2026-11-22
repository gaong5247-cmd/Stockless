"""UCI regression helpers must time out despite output and reap stuck engines."""
from __future__ import annotations

from pathlib import Path
import queue
import subprocess
import sys
import threading
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uci_lean_smoke as smoke


class UciSmokeTimeoutTests(unittest.TestCase):
    def test_info_messages_do_not_restart_the_deadline(self) -> None:
        lines = mock.Mock()
        lines.get.return_value = "info depth 1 nodes 1"
        with mock.patch.object(smoke.time, "monotonic", side_effect=[100.0, 100.0, 100.4, 100.8, 101.2]):
            with self.assertRaisesRegex(TimeoutError, "bestmove"):
                smoke.wait_for(lines, "bestmove ", seconds=1.0)
        waits = [call.kwargs["timeout"] for call in lines.get.call_args_list]
        self.assertEqual(len(waits), 3)
        for actual, expected in zip(waits, [1.0, 0.6, 0.2]):
            self.assertAlmostEqual(actual, expected)

    def test_expected_reply_and_unexpected_eof(self) -> None:
        lines: queue.Queue[str | None] = queue.Queue()
        lines.put("info string ready")
        lines.put("readyok")
        seen: list[str] = []
        self.assertEqual(smoke.wait_for(lines, "readyok", seen=seen), "readyok")
        self.assertEqual(seen, ["info string ready", "readyok"])
        lines.put(None)
        with self.assertRaisesRegex(RuntimeError, "closed stdout"):
            smoke.wait_for(lines, "bestmove ")

    def test_empty_queue_has_a_bounded_timeout(self) -> None:
        with self.assertRaises(TimeoutError):
            smoke.wait_for(queue.Queue(), "uciok", seconds=0.01)

    def test_unresponsive_process_uses_bounded_terminate_and_kill_waits(self) -> None:
        proc = mock.Mock()
        proc.poll.return_value = None
        proc.wait.side_effect = [subprocess.TimeoutExpired("fixture", 0.1),
                                 subprocess.TimeoutExpired("fixture", 0.2), -9]
        self.assertFalse(smoke.shutdown_engine(proc, grace_seconds=0.1, terminate_seconds=0.2))
        proc.terminate.assert_called_once()
        proc.kill.assert_called_once()
        self.assertEqual(proc.wait.call_args_list, [mock.call(timeout=0.1), mock.call(timeout=0.2),
                                                    mock.call(timeout=0.2)])

    def test_a_real_child_that_ignores_quit_is_reaped(self) -> None:
        proc = subprocess.Popen(
            [sys.executable, "-u", "-c",
             "import sys,time; print('readyok'); sys.stdin.readline(); time.sleep(30)"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", bufsize=1,
        )
        assert proc.stdout is not None and proc.stdin is not None
        lines: queue.Queue[str | None] = queue.Queue()
        reader = threading.Thread(target=lambda: lines.put(proc.stdout.readline().strip()), daemon=True)
        reader.start()
        try:
            smoke.wait_for(lines, "readyok", seconds=5.0)
            self.assertFalse(smoke.shutdown_engine(proc, grace_seconds=0.05, terminate_seconds=1.0))
            self.assertIsNotNone(proc.poll())
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=2.0)
            reader.join(timeout=2.0)
            proc.stdin.close()
            proc.stdout.close()


if __name__ == "__main__":
    unittest.main()
