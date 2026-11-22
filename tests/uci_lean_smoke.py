#!/usr/bin/env python3
"""UCI regression smoke for experimental lean Stockless (no ThreatHistory).

Unlike the deleted history-only test this exercises supported UCI search
settings, multiple searches and helper threads, and rejects stale options.
"""
from __future__ import annotations

import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path


def wait_for(lines: "queue.Queue[str | None]", prefix: str, seconds: float = 90.0,
             seen: list[str] | None = None) -> str:
    deadline = time.monotonic() + seconds
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("UCI did not send " + prefix)
            entry = lines.get(timeout=remaining)
            if entry is None:
                raise RuntimeError("Engine closed stdout before " + prefix)
            if seen is not None:
                seen.append(entry)
            if entry.startswith(prefix):
                return entry
    except queue.Empty as exc:
        raise TimeoutError("UCI did not send " + prefix) from exc


def shutdown_engine(proc: subprocess.Popen[str], grace_seconds: float = 5.0,
                    terminate_seconds: float = 2.0) -> bool:
    """Reap the process with bounded waits; return whether it exited normally."""
    if proc.poll() is not None:
        return proc.returncode == 0
    try:
        if proc.stdin is not None:
            proc.stdin.write("quit\n")
            proc.stdin.flush()
    except (BrokenPipeError, OSError):
        pass  # It may have exited between poll() and the write.
    try:
        proc.wait(timeout=grace_seconds)
        return proc.returncode == 0
    except subprocess.TimeoutExpired:
        proc.terminate()
    try:
        proc.wait(timeout=terminate_seconds)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=terminate_seconds)
    return False


def main() -> None:
    binary = Path(sys.argv[1] if len(sys.argv) > 1 else "build/stockless-src/src/stockless")
    config = (Path(__file__).resolve().parents[1] / "src/stockless/config.h").read_text()
    match = re.search(r'inline constexpr const char\* Version = "([^"]+)";', config)
    if match is None:
        raise AssertionError("Missing Stockless version")
    version = match.group(1)

    proc = subprocess.Popen(
        [str(binary.resolve())], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    assert proc.stdin and proc.stdout
    lines: queue.Queue[str | None] = queue.Queue()

    def reader() -> None:
        assert proc.stdout is not None
        try:
            for line in proc.stdout:
                lines.put(line.strip())
        finally:
            lines.put(None)

    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    def send(command: str) -> None:
        assert proc.stdin is not None
        proc.stdin.write(command + "\n")
        proc.stdin.flush()

    try:
        send("uci")
        header: list[str] = []
        wait_for(lines, "uciok", seen=header)
        expected = {
            f"id name Stockless {version}",
            "option name StocklessHybrid type check default true",
            "option name StocklessAggression type spin default 145 min 0 max 200",
            "option name StocklessThreats type check default true",
            "option name StocklessOverdrive type check default false",
        }
        missing = sorted(expected.difference(header))
        if missing:
            raise AssertionError(f"Missing UCI options: {missing}")
        forbidden = [
            option for option in header
            if option.startswith(("option name StocklessThreatHistory ",
                                  "option name StocklessHistoryWeight "))
        ]
        if forbidden:
            raise AssertionError(f"Retired options unexpectedly present: {forbidden}")

        for threads, hybrid, threats, aggression, overdrive in (
            (1, "true", "true", 145, "false"),
            (1, "false", "false", 0, "false"),
            (2, "true", "false", 96, "false"),
            (2, "true", "true", 145, "true"),
        ):
            for key, val in {
                "Threads": threads,
                "Hash": 16,
                "StocklessHybrid": hybrid,
                "StocklessThreats": threats,
                "StocklessAggression": aggression,
                "StocklessOverdrive": overdrive,
            }.items():
                send(f"setoption name {key} value {val}")
            send("ucinewgame")
            send("isready")
            wait_for(lines, "readyok")
            send("position startpos moves e2e4 e7e5 g1f3 b8c6")
            send("go depth 6")
            result = wait_for(lines, "bestmove ")
            if re.fullmatch(r"bestmove [a-h][1-8][a-h][1-8][qrbn]?"
                            r"(?: ponder [a-h][1-8][a-h][1-8][qrbn]?)?", result) is None:
                raise AssertionError(f"Unexpected bestmove: {result}")
            print(f"threads={threads} hybrid={hybrid} threats={threats}"
                  f" aggression={aggression} overdrive={overdrive}: {result}", flush=True)
    finally:
        # Popen's context manager waits without a timeout. Reap explicitly so a
        # broken engine cannot hang the regression job after a timeout/error.
        graceful = shutdown_engine(proc)
        proc.stdin.close()
        reader_thread.join(timeout=2.0)
        if not reader_thread.is_alive():
            proc.stdout.close()
    if not graceful:
        raise RuntimeError("Engine failed to exit cleanly after quit")
    print("PASS: lean UCI protocol, options and multi-search regression")


if __name__ == "__main__":
    main()
