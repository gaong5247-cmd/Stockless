"""Validate the complete output of the pinned Stockfish ``bench ... default depth``.

The position count comes from benchmark.cpp, not an engine's self-reported total.
uci.cpp sums the last full info's nodes for each position; no-move positions emit
only a depth-zero score and ``bestmove (none)``, and contribute zero nodes.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HEADER = re.compile(r"Position:\s+(\d+)/(\d+) \((.+)\)")
MOVE = r"[a-h][1-8][a-h][1-8][qrbn]?"
BESTMOVE = re.compile(rf"bestmove ({MOVE}|\(none\))(?: ponder ({MOVE}))?")
FULL_INFO = re.compile(
    r"info depth (\d+) seldepth (\d+) multipv 1 score (cp|mate) (-?\d+)"
    r"(?: (lowerbound|upperbound))?(?: wdl \d+ \d+ \d+)?"
    r" nodes (\d+) nps \d+ hashfull \d+ tbhits \d+ time \d+ pv (.+)"
)
NO_MOVES = re.compile(r"info depth 0 score (cp|mate) 0")
ITERATION = re.compile(rf"info depth \d+ currmove {MOVE} currmovenumber \d+")
SUMMARY = re.compile(r"(Total time \(ms\)|Nodes searched|Nodes/second)\s*:\s*(\d+)")


@dataclass(frozen=True)
class PositionResult:
    fen: str
    depth: int
    seldepth: int
    score: tuple[str, int, str | None]
    nodes: int
    pv: tuple[str, ...]
    bestmove: str
    ponder: str | None


@dataclass(frozen=True)
class BenchResult:
    nodes: int
    nps: int
    positions: tuple[PositionResult, ...]


def default_bench_position_count(source: Path | None = None) -> int:
    """Read the trusted pinned suite, excluding its UCI_Chess960 option lines."""
    source = source or ROOT / "upstream/stockfish/src/benchmark.cpp"
    text = source.read_text(encoding="utf-8")
    blocks = re.findall(
        r"const\s+std::vector<std::string>\s+Defaults\s*=\s*\{(.*?)\};", text, re.S
    )
    if len(blocks) != 1:
        raise ValueError(f"Cannot identify the pinned default bench suite in {source}")
    entries = re.findall(r'^\s*"([^"\n]+)"', blocks[0], re.M)
    positions = [entry for entry in entries if not entry.startswith("setoption ")]
    if not positions or any(not re.match(r"[prnbqkPRNBQK1-8/]+ [wb] ", fen) for fen in positions):
        raise ValueError(f"Invalid or empty pinned default bench suite in {source}")
    return len(positions)


def parse_bench(output: str, *, expected_positions: int, depth: int) -> BenchResult:
    """Reject partial, duplicated or inconsistent searches, even with a summary."""
    if expected_positions < 1 or depth < 1:
        raise ValueError("Expected position count and depth must be positive")
    positions: list[PositionResult] = []
    fen: str | None = None
    info: tuple[int, int, tuple[str, int, str | None], int, tuple[str, ...]] | None = None
    bestmove: tuple[str, str | None] | None = None
    summary: dict[str, int] = {}

    def finish_position() -> None:
        nonlocal fen, info, bestmove
        if fen is None:
            return
        number = len(positions) + 1
        if info is None or bestmove is None:
            raise ValueError(f"Position {number}: missing final info or bestmove")
        searched_depth, seldepth, score, nodes, pv = info
        move, ponder = bestmove
        if searched_depth == 0:
            if move != "(none)" or ponder is not None:
                raise ValueError(f"Position {number}: invalid no-move result")
        elif (searched_depth != depth or nodes <= 0 or not pv or move != pv[0]
              or (ponder is not None and (len(pv) < 2 or ponder != pv[1]))):
            raise ValueError(f"Position {number}: incomplete depth or inconsistent PV/bestmove")
        positions.append(PositionResult(fen, searched_depth, seldepth, score, nodes, pv, move, ponder))
        fen, info, bestmove = None, None, None

    for raw in output.splitlines():
        line = raw.strip()
        if match := HEADER.fullmatch(line):
            if summary:
                raise ValueError("Position appears after the bench summary")
            finish_position()
            number, total = int(match[1]), int(match[2])
            if number != len(positions) + 1 or total != expected_positions or number > total:
                raise ValueError("Bench position order/count disagrees with the pinned suite")
            fen = match[3]
        elif line.startswith("Position:"):
            raise ValueError("Malformed bench position header")
        elif match := FULL_INFO.fullmatch(line):
            if fen is None or bestmove is not None or summary:
                raise ValueError("Search info appears outside an unfinished position")
            pv = tuple(match[7].split())
            if not pv or any(re.fullmatch(MOVE, move) is None for move in pv):
                raise ValueError("Malformed principal variation")
            if int(match[1]) == 0:
                raise ValueError("A searched position must have positive depth")
            info = (int(match[1]), int(match[2]), (match[3], int(match[4]), match[5]),
                    int(match[6]), pv)
        elif match := NO_MOVES.fullmatch(line):
            if fen is None or info is not None or bestmove is not None or summary:
                raise ValueError("Unexpected no-move info")
            info = (0, 0, (match[1], 0, None), 0, ())
        elif line.startswith("info depth ") and not ITERATION.fullmatch(line):
            raise ValueError("Malformed or unsupported search info")
        elif match := BESTMOVE.fullmatch(line):
            if fen is None or bestmove is not None or summary:
                raise ValueError("Missing position or duplicate bestmove")
            bestmove = (match[1], match[2])
        elif line.startswith("bestmove"):
            raise ValueError("Malformed bestmove")
        elif match := SUMMARY.fullmatch(line):
            finish_position()
            if len(positions) != expected_positions:
                raise ValueError(f"Incomplete bench: {len(positions)}/{expected_positions} positions")
            key = match[1]
            if key in summary:
                raise ValueError(f"Duplicate bench summary: {key}")
            summary[key] = int(match[2])
        elif line.startswith(("Total time (ms)", "Nodes searched", "Nodes/second")):
            raise ValueError("Malformed bench summary")

    finish_position()
    if len(positions) != expected_positions or set(summary) != {
        "Total time (ms)", "Nodes searched", "Nodes/second"
    }:
        raise ValueError("Incomplete bench positions or summary")
    nodes, nps, elapsed = summary["Nodes searched"], summary["Nodes/second"], summary["Total time (ms)"]
    if nodes <= 0 or elapsed <= 0 or nps <= 0:
        raise ValueError("Bench totals must be positive")
    if nodes != sum(position.nodes for position in positions):
        raise ValueError("Bench total disagrees with per-position nodes")
    if nps != 1000 * nodes // elapsed:
        raise ValueError("Bench NPS disagrees with nodes and elapsed time")
    return BenchResult(nodes, nps, tuple(positions))
