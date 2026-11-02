"""Deterministic, entirely synthetic 30-task coding-agent pilot corpus.

These authored tasks are separate from the historical PR candidate study.
Answers and hidden inputs must never be placed in an agent workspace.
"""
from __future__ import annotations
import hashlib
import json
from collections import Counter

KIND_NAMES = ("clamp", "dedupe", "chunk", "median", "prefix",
              "interval", "frequency", "parse", "backoff", "search")
SPECS = [
    ("Clamp integers to the inclusive low/high limits.",
     "Wrap integers cyclically within the inclusive low/high range.",
     "Reflect values beyond either endpoint back into the inclusive range."),
    ("Remove exact duplicates while preserving first occurrences.",
     "Remove case-insensitive duplicates while preserving first original spelling.",
     "Trim surrounding spaces, discard case-insensitive duplicates and return trimmed values."),
    ("Partition items into all consecutive chunks of size n, keeping a short final chunk.",
     "Partition items into chunks of size n, padding the last chunk with null values.",
     "Partition items into chunks of size n, dropping incomplete trailing chunks."),
    ("Return the mathematical median; for even inputs average the two middle numbers.",
     "Return the lower median for even inputs; middle for odd inputs.",
     "Return the upper median for even inputs; middle for odd inputs."),
    ("Return the running sum after each numeric element; skip null elements.",
     "Return running sums, resetting the accumulator on null; emit null at a reset.",
     "Return the running maximum after each numeric element; skip null elements."),
    ("Merge sorted or unsorted closed intervals when they overlap or touch at an endpoint.",
     "Merge intervals only when they have a strictly positive overlap, not merely touch.",
     "Merge integer intervals when they overlap or their gap is at most one integer."),
    ("Return up to k unique items ranked by frequency descending, ties alphabetically.",
     "Return up to k unique items ranked by frequency descending, ties by first occurrence.",
     "Rank case-insensitive items by frequency descending, ties alphabetically in lowercase."),
    ("Parse semicolon-separated key=value pairs, trimming spaces; last duplicate wins.",
     "Parse semicolon-separated key=value pairs; first duplicate wins.",
     "Parse pipe-separated key=value pairs; permit empty values; last duplicate wins."),
    ("Return min(cap, base times two to the power of attempt).",
     "Return min(cap, base times attempt plus one).",
     "Return min(cap, base times three to the power of attempt)."),
    ("Find the first index of target or return minus one.",
     "Find the last index of target or return minus one.",
     "Return sorted insertion position of target, before any equal elements."),
]
BUGGY = (
    'def transform(d):\n    return min(d["low"], max(d["high"], d["value"]))\n',
    'def transform(d):\n    return sorted(set(d["items"]))\n',
    'def transform(d):\n    a, n = d["items"], d["n"]\n    return [a[i:i+n] for i in range(0, len(a), n+1)]\n',
    'def transform(d):\n    a = sorted(d["values"])\n    return a[0]\n',
    'def transform(d):\n    a = d["values"]\n    return [sum(x for x in a[:i] if x is not None) for i in range(len(a))]\n',
    'def transform(d):\n    return sorted(d["intervals"])\n',
    'def transform(d):\n    return sorted(d["items"])[:d["k"]]\n',
    'def transform(d):\n    return dict(pair.split("=") for pair in d["text"].split(";"))\n',
    'def transform(d):\n    return min(d["cap"], d["base"] * d["attempt"])\n',
    'def transform(d):\n    return d["items"].index(d["target"])\n',
)
INPUTS = [
    [{"low":1,"high":5,"value":7},{"low":-2,"high":2,"value":-3},
     {"low":0,"high":6,"value":13},{"low":2,"high":4,"value":-1},
     {"low":-3,"high":3,"value":30},{"low":3,"high":8,"value":3}],
    [{"items":["b","a","b","c"]},{"items":["Dog","dog","cat","CAT"]},
     {"items":[" A ","a","B"," b "]},{"items":[]},
     {"items":["x","x","X","y"]},{"items":[" a","a ","B","b"]}],
    [{"items":[1,2,3,4,5],"n":2},{"items":[9,8,7,6],"n":3},
     {"items":[],"n":2},{"items":[1,2,3,4,5,6,7],"n":3},
     {"items":[2],"n":4},{"items":[1,2,3,4],"n":2}],
    [{"values":[3,1,4,2]},{"values":[9,1,5]},{"values":[-3,0,-1,-2]},
     {"values":[8,8]},{"values":[3,6,3,9,10,12]},{"values":[5,1,2]}],
    [{"values":[1,2,3,4]},{"values":[5,None,3,2]},{"values":[-3,-1,-2]},
     {"values":[]},{"values":[2,0,-5,9]},{"values":[1,None,2,None,3]}],
    [{"intervals":[[1,3],[2,4],[7,8]]},{"intervals":[[1,2],[2,3]]},
     {"intervals":[[5,6],[1,4],[4,4]]},{"intervals":[]},
     {"intervals":[[1,5],[2,3],[10,11]]},{"intervals":[[-3,-2],[0,1]]}],
    [{"items":["b","a","b","c","a"],"k":2},{"items":["Dog","dog","cat","CAT"],"k":2},
     {"items":["z","a","z","b","a"],"k":3},{"items":[],"k":4},
     {"items":["A","a","b","B","c"],"k":2},{"items":["x","y","x","z"],"k":0}],
    [{"text":"a=1;b=2;a=3"},{"text":" a = x=y ; b = 2 "},
     {"text":"x=;y=3"},{"text":"a=1|b=2|a=4"},
     {"text":""},{"text":"q=hello=world;b="}],
    [{"base":2,"cap":20,"attempt":4},{"base":3,"cap":100,"attempt":0},
     {"base":1,"cap":15,"attempt":5},{"base":10,"cap":30,"attempt":2},
     {"base":4,"cap":4,"attempt":10},{"base":2,"cap":80,"attempt":3}],
    [{"items":[1,2,2,4],"target":2},{"items":[1,3,5],"target":2},
     {"items":[],"target":5},{"items":[5,5,5],"target":5},
     {"items":[1,2,3,4],"target":4},{"items":[1,3,3,7],"target":6}],
]


def oracle(kind: int, mode: int, d: dict):
    if kind == 0:
        lo, hi, v = d["low"], d["high"], d["value"]
        if mode == 0: return min(hi, max(lo, v))
        if mode == 1: return lo + (v-lo) % (hi-lo+1)
        if lo == hi: return lo
        width = hi-lo
        period = 2*width
        p = (v-lo) % period
        return lo + (p if p <= width else period-p)
    if kind == 1:
        out, seen = [], set()
        for s in d["items"]:
            value = s.strip() if mode == 2 else s
            key = value if mode == 0 else value.casefold()
            if key not in seen:
                out.append(value)
                seen.add(key)
        return out
    if kind == 2:
        items, n = d["items"], d["n"]
        out = [items[i:i+n] for i in range(0, len(items), n)]
        if mode == 1 and out: out[-1] += [None] * (n-len(out[-1]))
        if mode == 2: out = [part for part in out if len(part) == n]
        return out
    if kind == 3:
        a = sorted(d["values"]); n = len(a)
        if n % 2: return a[n//2]
        if mode == 0: return (a[n//2-1] + a[n//2]) / 2
        return a[n//2-1] if mode == 1 else a[n//2]
    if kind == 4:
        out, acc = [], 0
        for value in d["values"]:
            if mode == 1 and value is None:
                acc = 0
                out.append(None)
                continue
            if value is None: continue
            acc = max(acc, value) if mode == 2 and out else acc+value
            out.append(acc)
        return out
    if kind == 5:
        out = []
        for lo, hi in sorted(d["intervals"]):
            gap = 0 if mode == 0 else (-1 if mode == 1 else 2)
            if out and lo <= out[-1][1] + gap:
                out[-1][1] = max(hi, out[-1][1])
            else:
                out.append([lo,hi])
        return out
    if kind == 6:
        a, k = d["items"], d["k"]
        keys = [s.casefold() if mode == 2 else s for s in a]
        count = Counter(keys)
        order = {s: keys.index(s) for s in count}
        return sorted(count, key=lambda s: (-count[s],order[s] if mode == 1 else s))[:k]
    if kind == 7:
        out = {}
        sep = "|" if mode == 2 else ";"
        for pair in d["text"].split(sep):
            if not pair or "=" not in pair: continue
            key, value = pair.split("=", 1)
            key, value = key.strip(), value.strip()
            if mode != 1 or key not in out: out[key] = value
        return out
    if kind == 8:
        b, cap, i = d["base"], d["cap"], d["attempt"]
        return min(cap, b * ((i+1) if mode == 1 else (2 if mode == 0 else 3)**i))
    if kind == 9:
        a, x = d["items"], d["target"]
        if mode == 2:
            return next((i for i, v in enumerate(a) if v >= x), len(a))
        hits = [i for i, v in enumerate(a) if v == x]
        return (hits[0] if mode == 0 else hits[-1]) if hits else -1
    raise ValueError(kind)


def task(index: int):
    if index < 0 or index >= 30: raise ValueError(index)
    kind, mode = divmod(index, 3)
    # Two visible tests; the remaining four are sealed from the agent's worktree.
    pool = INPUTS[kind]
    public = [{"input": x, "expected": oracle(kind, mode, x)} for x in pool[:2]]
    hidden = [{"input": x, "expected": oracle(kind, mode, x)} for x in pool[2:]]
    return {"task_id": f"FWE-{index+1:03d}", "kind": KIND_NAMES[kind],
            "mode": mode, "spec": SPECS[kind][mode],
            "source": BUGGY[kind], "public": public, "hidden": hidden}


def fingerprint():
    payload = [task(i) for i in range(30)]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def public_test_code(t: dict) -> str:
    cases = repr([(r["input"], r["expected"]) for r in t["public"]])
    return ("import unittest\nfrom solution import transform\n"
            "class PublicTest(unittest.TestCase):\n"
            "    def test_examples(self):\n"
            f"        for inp, expected in {cases}:\n"
            "            with self.subTest(inp=inp):\n"
            "                self.assertEqual(transform(inp), expected)\n")


def hidden_test_code(t: dict) -> str:
    cases = repr([(r["input"], r["expected"]) for r in t["hidden"]])
    return ("import unittest\nfrom solution import transform\n"
            "class HiddenTest(unittest.TestCase):\n"
            "    def test_held_out(self):\n"
            f"        for inp, expected in {cases}:\n"
            "            with self.subTest(inp=inp):\n"
            "                self.assertEqual(transform(inp), expected)\n")
