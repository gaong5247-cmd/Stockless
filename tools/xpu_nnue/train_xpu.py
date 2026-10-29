#!/usr/bin/env python3
"""Independent continuous Intel XPU optimizer for Stockless's native NNUE FC2.

Frozen: Stockfish HalfKAv2_hm + FullThreats + PP_3Wide transformer, FC0, FC1,
PSQT and skip. Trainable: each of eight FC2 weight vectors and biases.
This is a precise scope: NOT a whole-network trainer; architecture untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
import signal
import time
from pathlib import Path

import numpy as np
import torch

from net_format import base_weights, read_net, write_final_layers

DTYPE = np.dtype([
    ("bucket", "u1"), ("features", "u1", (128,)),
    ("psqt", "<i4"), ("skip", "<i4"), ("raw", "<i4"), ("teacher", "<i4"),
    ("attack", "<f4"), ("win", "<f4"), ("loss", "<f4"),
])
assert DTYPE.itemsize == 157
FACTOR = 600 / (128 * 64 * 2)
STOP = False


def request_stop(sig, frame):
    global STOP
    STOP = True
    print("\nCtrl+C received: saving safely after current minibatch.", flush=True)


def atomic_save(obj, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    torch.save(obj, temp)
    os.replace(temp, path)


def load_data(path):
    path = Path(path)
    if path.stat().st_size == 0 or path.stat().st_size % DTYPE.itemsize:
        raise ValueError(f"Corrupt / empty training file: {path}")
    return np.memmap(path, mode="r", dtype=DTYPE)


def features_to_tensors(rows, device):
    # Gather CPU pageable records first; transfer only one batch to Intel XPU.
    def tensor(name, dtype=torch.float32):
        return torch.as_tensor(np.asarray(rows[name]).copy(), dtype=dtype, device="cpu").to(device)
    bucket = tensor("bucket", torch.long)
    acts = tensor("features")
    return (bucket, acts, tensor("psqt"), tensor("skip"), tensor("raw"),
            tensor("teacher"), tensor("attack"), tensor("win"), tensor("loss"))


def predict(params, t):
    bucket, acts, psqt, skip, raw, teacher, attack, win, loss = t
    weights, biases = params
    return psqt / 16.0 + (torch.sum(acts * weights[bucket], dim=1)
                          + biases[bucket] + skip) * FACTOR


def targets(t, teacher_mix, attack_cp, cap_native):
    bucket, acts, psqt, skip, raw, teacher, attack, win, loss = t
    # Teacher's searched score is NOT a direct NNUE value. Limit its
    # influence and anchor target to the unmodified network's native score.
    correction = (teacher - raw).clamp(-cap_native, cap_native) * teacher_mix
    # Aggression preference only in teacher-evaluated non-losing situations.
    safe = ((win >= loss) & (teacher > -40)).float()
    reward = attack * safe * attack_cp * 2.5  # conservative native-unit proxy
    return raw + correction + reward


@torch.no_grad()
def validate(params, rows, device, batch, mix, bonus, cap, max_rows=25000):
    if len(rows) == 0:
        return float("inf")
    err, count = 0.0, 0
    for i in range(0, min(len(rows), max_rows), batch):
        t = features_to_tensors(rows[i:i + batch], device)
        p = predict(params, t)
        y = targets(t, mix, bonus, cap)
        err += ((p - y) ** 2).sum().item()
        count += len(p)
    return math.sqrt(err / max(1, count))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-net", required=True)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("training_runs/stockless_xpu"))
    ap.add_argument("--batch-size", type=int, default=2048)
    ap.add_argument("--lr", type=float, default=0.001)
    ap.add_argument("--save-every", type=int, default=500)
    ap.add_argument("--teacher-mix", type=float, default=0.08)
    ap.add_argument("--attack-cp", type=float, default=8.0)
    ap.add_argument("--seed", type=int, default=5247)
    args = ap.parse_args()
    if not torch.xpu.is_available():
        raise SystemExit("Intel XPU unavailable. Requires an Intel XPU PyTorch installation; CPU fallback is disabled.")
    if args.batch_size < 1 or args.save_every < 1 or not 0 <= args.teacher_mix <= 0.2:
        ap.error("Invalid batch/save/mix")
    read_net(args.base_net)  # fail closed on incompatible architecture
    initial_bias, initial_w = base_weights(args.base_net)
    filehash = hashlib.sha256(Path(args.base_net).read_bytes()).hexdigest()
    device = torch.device("xpu")
    train = load_data(args.data / "train.bin")
    val = load_data(args.data / "val.bin")
    orig_w = torch.tensor(initial_w, dtype=torch.float32, device=device)
    orig_b = torch.tensor(initial_bias, dtype=torch.float32, device=device)
    weights = torch.nn.Parameter(orig_w.clone())
    biases = torch.nn.Parameter(orig_b.clone())
    params = (weights, biases)
    optimizer = torch.optim.AdamW([weights, biases], lr=args.lr, weight_decay=0.0)
    args.out.mkdir(parents=True, exist_ok=True)
    checkpoint = args.out / "latest.pt"
    epoch, start, step, best = 0, 0, 0, float("inf")
    rng = np.random.default_rng(args.seed)
    if checkpoint.exists():
        saved = torch.load(checkpoint, map_location="cpu", weights_only=False)
        if saved["base_hash"] != filehash or saved["data_bytes"] != (train.nbytes, val.nbytes):
            raise RuntimeError("Checkpoint base net/data changed; refusing unsafe resume")
        with torch.no_grad():
            weights.copy_(saved["weights"].to(device))
            biases.copy_(saved["biases"].to(device))
        optimizer.load_state_dict(saved["optimizer"])
        epoch, start, step, best = saved["epoch"], saved["start"], saved["step"], saved["best"]
        rng.bit_generator.state = saved["rng_state"]
        print(f"Resumed epoch={epoch}, offset={start}, global_step={step}")
    signal.signal(signal.SIGINT, request_stop)

    def save(label="latest"):
        # Export quantized parameters, preserving every original NNUE byte
        # except eight last layers. The unmodified base remains immutable.
        with torch.no_grad():
            q_w = torch.round(weights.clamp(-128, 127)).cpu().numpy()
            q_b = torch.round(biases.clamp(-(2**31), 2**31 - 1024)).cpu().numpy()
        state = {
            "weights": weights.detach().cpu(), "biases": biases.detach().cpu(),
            "optimizer": optimizer.state_dict(), "base_hash": filehash,
            "data_bytes": (train.nbytes, val.nbytes),
            "epoch": epoch, "start": start, "step": step, "best": best,
            "rng_state": rng.bit_generator.state,
        }
        atomic_save(state, args.out / (label + ".pt"))
        write_final_layers(args.base_net, args.out / (label + ".nnue"), q_b, q_w)
        print(f"Saved {label}.pt/.nnue at step={step}", flush=True)

    while True:
        # Reconstruct deterministic reshuffling for exact offset resume.
        seed = args.seed + epoch
        order = np.random.default_rng(seed).permutation(len(train))
        for offset in range(start, len(train), args.batch_size):
            t = features_to_tensors(train[order[offset:offset + args.batch_size]], device)
            prediction = predict(params, t)
            desired = targets(t, args.teacher_mix, args.attack_cp, 45.0)
            regularize = 0.001 * ((weights - orig_w) ** 2).mean()
            regularize += 0.00001 * ((biases - orig_b) ** 2).mean()
            loss = torch.nn.functional.smooth_l1_loss(prediction, desired, beta=20.0) + regularize
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_([weights, biases], 100.0)
            optimizer.step()
            with torch.no_grad():
                weights.clamp_(-128, 127)
                biases.clamp_(-(2**31), 2**31 - 1024)
            step += 1
            start = min(offset + args.batch_size, len(train))
            if step % 100 == 0:
                print(f"epoch={epoch} seen={start:,}/{len(train):,} step={step} loss={loss.item():.5f}", flush=True)
            if step % args.save_every == 0 or STOP:
                save()
            if STOP:
                return
        start = 0
        epoch += 1
        rmse = validate(params, val, device, args.batch_size,
                        args.teacher_mix, args.attack_cp, 45.0)
        print(f"epoch={epoch} validation_rmse(native_units)={rmse:.4f}", flush=True)
        if rmse < best:
            best = rmse
            save("best")
        save()


if __name__ == "__main__":
    main()
