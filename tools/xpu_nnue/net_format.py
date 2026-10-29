"""Pinned-Stockfish (0a215d6) .nnue final-layer reader/writer.

The original feature transformer and ALL other bytes are copied verbatim.
Fails closed if the network does not match the known 8-bucket architecture.
"""
from __future__ import annotations

import os
import struct
from pathlib import Path

VERSION = 0x6A448AFA
BUCKETS = 8
FC0_IN, FC0_OUT = 1024, 32
FC1_IN, FC1_OUT = 64, 32
FC2_IN = 128

# Per-layer serialization (little-endian biases, then signed i8 weights).
FC0_BYTES = FC0_OUT * 4 + FC0_IN * FC0_OUT
FC1_BYTES = FC1_OUT * 4 + FC1_IN * FC1_OUT
FC2_BYTES = 4 + FC2_IN
STACK_BYTES = 4 + FC0_BYTES + FC1_BYTES + FC2_BYTES
FINAL_OFFSET = 4 + FC0_BYTES + FC1_BYTES


class UnsupportedNetwork(ValueError):
    pass


def read_net(path: str | Path):
    path = Path(path)
    blob = path.read_bytes()
    if len(blob) < 16 + STACK_BYTES * BUCKETS:
        raise UnsupportedNetwork("NNUE too small")
    version, net_hash, desc_len = struct.unpack_from("<III", blob, 0)
    if version != VERSION or desc_len > 8192 or 12 + desc_len >= len(blob):
        raise UnsupportedNetwork("Unsupported NNUE header/version")
    desc = blob[12:12 + desc_len].decode("utf-8", errors="replace")
    stacks_start = len(blob) - STACK_BYTES * BUCKETS
    if stacks_start <= 12 + desc_len + 4:
        raise UnsupportedNetwork("Missing compressed feature transformer")
    hashes = []
    params = []
    for bucket in range(BUCKETS):
        pos = stacks_start + bucket * STACK_BYTES
        layer_hash, = struct.unpack_from("<I", blob, pos)
        hashes.append(layer_hash)
        final = pos + FINAL_OFFSET
        bias, = struct.unpack_from("<i", blob, final)
        weights = list(struct.unpack_from("<128b", blob, final + 4))
        params.append((bias, weights))
    if len(set(hashes)) != 1 or hashes[0] == 0:
        raise UnsupportedNetwork("Bucket layer hashes mismatch")
    # Validate format markers in the transformer payload, not merely tail size.
    ft = blob[12 + desc_len:stacks_start]
    if b"COMPRESSED_LEB128" not in ft or len(ft) < 1024:
        raise UnsupportedNetwork("Expected pinned Stockfish compressed transformer")
    return blob, stacks_start, params, desc


def write_final_layers(source: str | Path, destination: str | Path, biases, weights):
    blob, start, original, desc = read_net(source)
    if len(biases) != BUCKETS or len(weights) != BUCKETS:
        raise ValueError("Expected eight final layers")
    patched = bytearray(blob)
    for i in range(BUCKETS):
        b = int(round(float(biases[i])))
        w = [int(round(float(x))) for x in weights[i]]
        if not -(2**31) <= b < 2**31 or len(w) != 128 or any(not -128 <= x <= 127 for x in w):
            raise ValueError("Quantized values out of range")
        off = start + i * STACK_BYTES + FINAL_OFFSET
        struct.pack_into("<i128b", patched, off, b, *w)
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    with tmp.open("wb") as f:
        f.write(patched)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, dest)
    check, _, current, _ = read_net(dest)
    if len(check) != len(blob):
        raise RuntimeError("Exported NNUE length changed")
    # No accidental changes to transformer or earlier layers.
    for i in range(BUCKETS):
        off = start + i * STACK_BYTES + FINAL_OFFSET
        if patched[off:off + FC2_BYTES] != check[off:off + FC2_BYTES]:
            raise RuntimeError("Final layer mismatch after export")
    return desc


def base_weights(path: str | Path):
    _, _, pairs, _ = read_net(path)
    return [x[0] for x in pairs], [x[1] for x in pairs]
