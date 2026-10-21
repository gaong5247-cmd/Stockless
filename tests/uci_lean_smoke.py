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
from pathlib import Path


def wait_for(lines: "queue.Queue[str | None]", prefix: str, seconds: float = 90.0,
             seen: list[str] | None = None) -> str:
    try:
        while True:
            entry = lines.get(timeout=seconds)
            if entry is None:
                raise RuntimeError("Engine closed stdout before " + prefix)
            if seen is not None:
                seen.append(entry)
            if entry.startswith(prefix):
                return entry
    except queue.Empty as exc:
        raise TimeoutError("UCI did not send " + prefix) from exc


def main() -> None:
    binary = Path(sys.argv[1] if len(sys.argv) > 1 else "build/stockless-src/src/stockless")
    config = (Path(__file__).resolve().parents[1] / "src/stockless/config.h").read_text()
    match = re.search(r'inline constexpr const char\* Version = "([^"]+)";', config)
    if match is None:
        raise AssertionError("Missing Stockless version")
    version = match.group(1)

    with subprocess.Popen(
        [str(binary.resolve())], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1,
    ) as proc:
        assert proc.stdin and proc.stdout
        lines: queue.Queue[str | None] = queue.Queue()

        def reader() -> None:
            for line in proc.stdout:
                lines.put(line.strip())
            lines.put(None)

        threading.Thread(target=reader, daemon=True).start()

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
                if result.split()[1] in ("(none)", "0000"):
                    raise AssertionError(f"Unexpected bestmove: {result}")
                print(f"threads={threads} hybrid={hybrid} threats={threats}"
                      f" aggression={aggression} overdrive={overdrive}: {result}", flush=True)
            print("PASS: lean UCI protocol, options and multi-search regression")
        finally:
            if proc.poll() is None:
                send("quit")


if __name__ == "__main__":
    main()
