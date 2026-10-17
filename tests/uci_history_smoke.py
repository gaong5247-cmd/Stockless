#!/usr/bin/env python3
"""UCI search smoke for StocklessThreatHistory OFF and ON.

Runs a real search at depth 6, not just a UCI option enumeration.
"""
from __future__ import annotations

import queue
import subprocess
import sys
import threading
import time
from pathlib import Path


def wait_for(lines: "queue.Queue[str | None]", prefix: str, seconds: float = 60.0, collected: list[str] | None = None) -> str:
    deadline = time.monotonic() + seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"UCI timeout waiting for {prefix}")
        try:
            line = lines.get(timeout=remaining)
        except queue.Empty:
            raise TimeoutError(f"UCI timeout waiting for {prefix}") from None
        if line is None:
            raise RuntimeError(f"Engine exited before {prefix}")
        if collected is not None:
            collected.append(line)
        if line.startswith(prefix):
            return line


def main() -> None:
    binary = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("build/stockless-src/src/stockless")
    )
    with subprocess.Popen(
        [str(binary.resolve())],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    ) as proc:
        assert proc.stdin is not None
        assert proc.stdout is not None
        lines: queue.Queue[str | None] = queue.Queue()

        def reader() -> None:
            for line in proc.stdout:
                lines.put(line.strip())
            lines.put(None)

        threading.Thread(target=reader, daemon=True).start()

        def send(command: str) -> None:
            proc.stdin.write(command + "\n")
            proc.stdin.flush()

        try:
            send("uci")
            header: list[str] = []
            wait_for(lines, "uciok", collected=header)
            required = {
                "id name Stockless v0.7",
                "option name StocklessHybrid type check default true",
                "option name StocklessAggression type spin default 145 min 0 max 200",
                "option name StocklessThreats type check default true",
                "option name StocklessOverdrive type check default false",
                "option name StocklessThreatHistory type check default false",
                "option name StocklessHistoryWeight type spin default 100 min 0 max 200",
            }
            missing = sorted(required.difference(header))
            if missing:
                raise AssertionError(f"Incorrect v0.7 UCI header: missing {missing}; got {header}")
            print("UCI identity Stockless v0.7 and recommended defaults verified")
            send("setoption name Threads value 1")
            send("setoption name Hash value 32")
            send("setoption name StocklessOverdrive value false")
            for enabled in ("false", "true"):
                send("ucinewgame")
                send(f"setoption name StocklessThreatHistory value {enabled}")
                send("setoption name StocklessHistoryWeight value 100")
                send("isready")
                wait_for(lines, "readyok")
                send("position startpos")
                send("go depth 6")
                best = wait_for(lines, "bestmove ", 60.0)
                if best.split()[1] in {"(none)", "0000"}:
                    raise AssertionError(f"Unexpected bestmove: {best}")
                print(f"ThreatHistory={enabled}: {best}")
        finally:
            if proc.poll() is None:
                send("quit")


if __name__ == "__main__":
    main()
