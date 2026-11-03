#!/usr/bin/env python3
"""Bounded research-only neural architecture search with retained evidence.

PyTorch is required for experiments but is not a FAR package dependency.
No generated arbitrary Python, model-provider claims, or production changes.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import itertools
import json
import math
import os
import platform
import random
import time
import traceback
from pathlib import Path

TASKS = ("remember_first", "xor_endpoints", "majority")
OPS = ("attn", "gru", "conv")
BASES = (("identity",), ("attn",), ("gru",), ("conv",))
VERSION = "far-model-architecture-search/0.1"


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def identity(recipe):
    return "+".join(recipe)


def validate_recipe(r, max_blocks):
    if not isinstance(r, (tuple, list)) or not 1 <= len(r) <= max_blocks:
        raise ValueError("invalid recipe length")
    if tuple(r) == ("identity",):
        return ("identity",)
    if any(type(v) is not str or v not in OPS for v in r):
        raise ValueError("unknown mixer")
    return tuple(r)


def positive(p, key, lo, hi):
    v = p[key]
    if type(v) is not int or not lo <= v <= hi:
        raise ValueError(f"{key} must be integer in {lo}..{hi}")
    return v


def validate_protocol(p):
    required = {"version", "study_id", "search_seed", "data_seed", "sequence_length",
                "train_size", "validation_size", "test_size", "width", "steps",
                "batch_size", "learning_rate", "max_candidates", "max_blocks",
                "selection_train_seed", "final_train_seeds", "tasks", "device"}
    if type(p) is not dict or set(p) != required:
        raise ValueError("protocol field set mismatch")
    if p["version"] != VERSION or p["device"] != "cpu" or p["tasks"] != list(TASKS):
        raise ValueError("unsupported protocol version, device, or task family")
    if type(p["study_id"]) is not str or not p["study_id"].strip():
        raise ValueError("study id required")
    for k in ("search_seed", "data_seed", "selection_train_seed"):
        positive(p, k, 0, 2**31 - 1)
    n = positive(p, "sequence_length", 7, 20)
    sizes = [positive(p, k, 16, 65536) for k in ("train_size", "validation_size", "test_size")]
    if sum(sizes) > 2**n:
        raise ValueError("not enough distinct binary sequences for disjoint splits")
    positive(p, "width", 8, 128)
    positive(p, "steps", 1, 3000)
    positive(p, "batch_size", 1, sizes[0])
    positive(p, "max_blocks", 2, 4)
    positive(p, "max_candidates", 4, 24)
    if p["max_candidates"] > 1 + sum(len(OPS)**i for i in range(1, p["max_blocks"]+1)):
        raise ValueError("search budget exceeds operator search space")
    if type(p["learning_rate"]) not in (int, float) or not math.isfinite(p["learning_rate"]) or not 0 < p["learning_rate"] <= 0.1:
        raise ValueError("invalid learning rate")
    seeds = p["final_train_seeds"]
    if type(seeds) is not list or not 2 <= len(seeds) <= 10 or len(set(map(str, seeds))) != len(seeds):
        raise ValueError("final seeds must be 2..10 distinct integers")
    for seed in seeds:
        if type(seed) is not int or not 0 <= seed <= 2**31 - 1:
            raise ValueError("invalid final seed")
    if p["selection_train_seed"] in seeds:
        raise ValueError("selection and final training seeds overlap")
    return p


def splits_for(p):
    n = sum(p[k] for k in ("train_size", "validation_size", "test_size"))
    values = random.Random(p["data_seed"]).sample(range(2**p["sequence_length"]), n)
    a, b = p["train_size"], p["validation_size"]
    return {"train": values[:a], "validation": values[a:a+b], "test": values[a+b:]}


def bits_of(value, length):
    return [(value >> i) & 1 for i in range(length-1, -1, -1)]


def label(bits, task):
    if task == "remember_first":
        return bits[0]
    if task == "xor_endpoints":
        return bits[0] ^ bits[-1]
    if task == "majority":
        return int(sum(bits) > len(bits)//2)
    raise ValueError("unknown task")


def rank(rec):
    return (-rec["validation"]["macro_accuracy"], rec["parameters"], identity(rec["recipe"]))


def next_recipe(records, rng, max_blocks):
    seen = {tuple(x["recipe"]) for x in records}
    top = sorted(records, key=rank)[:2]
    for _ in range(128):
        parent = rng.choice(top)
        recipe = list(parent["recipe"])
        if recipe == ["identity"]:
            recipe = []
        move = rng.choice(("replace", "insert", "delete"))
        if move == "replace" and recipe:
            i = rng.randrange(len(recipe))
            recipe[i] = rng.choice([op for op in OPS if op != recipe[i]])
        elif move == "insert" and len(recipe) < max_blocks:
            recipe.insert(rng.randrange(len(recipe)+1), rng.choice(OPS))
        elif move == "delete" and recipe:
            recipe.pop(rng.randrange(len(recipe)))
        else:
            continue
        candidate = tuple(recipe or ["identity"])
        if candidate not in seen:
            return candidate, identity(parent["recipe"])
    for size in range(1, max_blocks+1):
        for recipe in itertools.product(OPS, repeat=size):
            if recipe not in seen:
                return recipe, "enumeration-fallback"
    raise RuntimeError("search space exhausted")

