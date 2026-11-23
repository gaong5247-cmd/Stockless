"""Fast unit tests; do not require a GPU or installed Stockfish network."""
from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "xpu_nnue"))
from net_format import (VERSION, STACK_BYTES, BUCKETS, FC2_BYTES,
                        FINAL_OFFSET, UnsupportedNetwork, read_net,
                        base_weights, write_final_layers)


class TestNativeNnueSerialization(unittest.TestCase):
    def fake_net(self, path):
        desc = b"synthetic test network"
        transformer = b"COMPRESSED_LEB128" + bytes(1900)
        result = bytearray(struct.pack("<III", VERSION, 0xA1B2C3D4, len(desc)) + desc
                           + transformer + bytes(STACK_BYTES * BUCKETS))
        begin = 12 + len(desc) + len(transformer)
        for i in range(BUCKETS):
            pos = begin + i * STACK_BYTES
            struct.pack_into("<I", result, pos, 0x1234ABCD)
            struct.pack_into("<i128b", result, pos + FINAL_OFFSET, i * 17,
                             *([i - 4] * 128))
        path.write_bytes(result)
        return bytes(result), begin

    def test_only_last_layer_changes(self):
        with tempfile.TemporaryDirectory() as d:
            base, dest = Path(d) / "base.nnue", Path(d) / "converted.nnue"
            original, first = self.fake_net(base)
            blob, start, params, desc = read_net(base)
            self.assertEqual(start, first)
            self.assertEqual(params[7][0], 119)
            biases, weights = base_weights(base)
            new_biases = [x + 100 for x in biases]
            new_weights = [[x + 1 for x in row] for row in weights]
            write_final_layers(base, dest, new_biases, new_weights)
            self.assertEqual(dest.stat().st_size, base.stat().st_size)
            result = dest.read_bytes()
            for i in range(BUCKETS):
                off = first + i * STACK_BYTES + FINAL_OFFSET
                self.assertEqual(result[:off] if i == 0 else result[off - 10:off],
                                 original[:off] if i == 0 else original[off - 10:off])
                self.assertEqual(result[off:off + 4], struct.pack("<i", new_biases[i]))
                self.assertEqual(result[off + FC2_BYTES:off + STACK_BYTES - FINAL_OFFSET],
                                 original[off + FC2_BYTES:off + STACK_BYTES - FINAL_OFFSET])
            self.assertEqual(base.read_bytes(), original)

    def test_unknown_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.nnue"
            self.fake_net(path)
            raw = bytearray(path.read_bytes())
            raw[0] = 0
            path.write_bytes(raw)
            with self.assertRaises(UnsupportedNetwork):
                read_net(path)

    def test_quantized_range_checked(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / "base.nnue"
            self.fake_net(base)
            biases, weights = base_weights(base)
            weights[0][0] = 1000
            with self.assertRaises(ValueError):
                write_final_layers(base, Path(d) / "out.nnue", biases, weights)


if __name__ == "__main__":
    unittest.main()
