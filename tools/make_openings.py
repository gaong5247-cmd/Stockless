#!/usr/bin/env python3
import sys
import chess

src = sys.argv[1]
dst = sys.argv[2]

count = 0
with open(src, "r", encoding="utf-8") as inp, open(dst, "w", encoding="utf-8") as out:
    for lineno, raw in enumerate(inp, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        board = chess.Board()
        for token in line.split():
            try:
                move = chess.Move.from_uci(token)
            except ValueError as exc:
                raise SystemExit(f"{src}:{lineno}: bad UCI move {token}: {exc}")
            if move not in board.legal_moves:
                raise SystemExit(f"{src}:{lineno}: illegal move {token} in {board.fen()}")
            board.push(move)
        out.write(board.epd() + "\n")
        count += 1

print(f"wrote {count} legal opening positions to {dst}")
