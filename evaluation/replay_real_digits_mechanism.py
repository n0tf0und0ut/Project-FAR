"""Independent checkpoint replay through PyTorch forward hooks.

Arguments are output files of evaluation.run_real_digits_mechanism.
Requires optional torch, numpy, scikit-learn. Does NOT retrain the model;
it reconstructs weights and performs an independent intervention path with
a forward hook rather than the generation script's manual hidden replacement.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path


def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def digest(blob):
    return sha256(blob).hexdigest()


def replay(checkpoint_path: Path, trace_path: Path):
    import numpy as np
    import torch
    from sklearn.datasets import load_digits
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    doc = json.loads(trace_path.read_text(encoding="utf-8"))
    if digest(canonical(checkpoint)) != doc["model"]["artifact_sha256"]:
        raise ValueError("checkpoint commitment mismatch")
    if digest(load_digits().data.astype(np.float32).tobytes()) != checkpoint["dataset_sha256"]:
        raise ValueError("dataset bytes mismatch")
    if digest(canonical(checkpoint["indices_train"])) != doc["model"]["reference_population_sha256"]:
        raise ValueError("training split commitment mismatch")

    class Network(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = torch.nn.Linear(64, 24)
            self.fc2 = torch.nn.Linear(24, 10)

        def forward(self, x):
            return self.fc2(torch.relu(self.fc1(x)))

    def probs(logits):
        z = np.asarray(logits, dtype=np.float64) / 2
        a = np.exp(z - z.max())
        p = 0.995 * (a / a.sum()) + 0.005 / len(a)
        integer = np.floor(p * 1_000_000).astype(int)
        remaining = 1_000_000 - int(integer.sum())
        frac = p * 1_000_000 - integer
        if remaining > 0:
            order = sorted(range(len(p)), key=lambda i: (-frac[i], i))
            for i in order[:remaining]:
                integer[i] += 1
        elif remaining < 0:
            order = sorted(range(len(p)), key=lambda i: (frac[i], i))
            for i in order[:abs(remaining)]:
                integer[i] -= 1
        return np.asarray(integer, dtype=np.int64) / 1_000_000

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    model = Network()
    state = {key: torch.tensor(values, dtype=torch.float32).reshape(
             checkpoint["shapes"][key])
             for key, values in checkpoint["weights"].items()}
    model.load_state_dict(state, strict=True)
    model.eval()
    unit = checkpoint["hidden_unit"]
    max_error = 0.0

    with torch.no_grad():
        for case in doc["cases"]:
            index = int(case["id"].split("-")[1])
            values = np.asarray(checkpoint["cases"][str(index)], dtype=np.float32)
            if digest(values.tobytes()) != case["input_sha256"]:
                raise ValueError("sample input digest mismatch: " + case["id"])
            if values.shape != (64,):
                raise ValueError("invalid input dimensions")
            inp = torch.from_numpy(values[None, :])
            normal_activation = float(torch.relu(model.fc1(inp))[0, unit])
            if abs(normal_activation - float(case["observed_activation"])) > 1e-5:
                raise ValueError("original hidden activation mismatch")

            for condition, expected, replacement in (
                ("original", case["original_probs"], None),
                ("replacement", case["replacement_probs"], float(case["explained_activation"])),
                ("baseline", case["baseline_probs"], float(case["baseline_activation"])),
            ):
                if replacement is None:
                    logits = model(inp)
                else:
                    def patch(_module, _inputs, pre_relu):
                        new = pre_relu.clone()
                        new[:, unit] = replacement
                        return new
                    handle = model.fc1.register_forward_hook(patch)
                    try:
                        logits = model(inp)
                    finally:
                        handle.remove()
                actual = probs(logits.detach().numpy()[0])
                expected = np.asarray([float(v) for v in expected])
                discrepancy = float(np.max(np.abs(actual - expected)))
                max_error = max(max_error, discrepancy)
                if discrepancy > 0.000002:
                    raise ValueError(f"replay mismatch {case['id']} {condition}: {discrepancy}")

    return {
        "status": "SAVED_WEIGHT_MODEL_REPLAY_VERIFIED",
        "n": len(doc["cases"]),
        "checkpoint_sha256": doc["model"]["artifact_sha256"],
        "max_absolute_probability_deviation": max_error,
        "replay_method": "PyTorch forward hook on fc1 pre-ReLU output",
        "assurance": "SAVED_CHECKPOINT_REPLAY_NOT_INDEPENDENT_SOURCE_OR_SEMANTIC_VERIFICATION",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("traces", type=Path)
    args = parser.parse_args()
    print(json.dumps(replay(args.checkpoint, args.traces), indent=2))


if __name__ == "__main__":
    main()
