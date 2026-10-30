"""Reproducible *real-trained-network* activation replacement experiment.

Optional external dependencies (not part of canonical FAR test requirements):
  torch, numpy, scikit-learn

Trains a 64->24->10 MLP on scikit-learn's real handwritten-digit images,
fits a simple hypothesis to training activations, then actually intervenes at
a hidden ReLU neuron during inference. Exports FAR-MECH/0.1 source-bound traces,
a serialized CPU checkpoint and an evaluated report.

NOT an LLM or frontier-model mechanistic interpretation benchmark. The
adversarial cohort is selected post hoc for *failure discovery*, not an
unbiased confirmatory effect estimate.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

SEED = 1729
MICRO = 1_000_000


def _canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def run(output: Path):
    try:
        import numpy as np
        import torch
        from sklearn.datasets import load_digits
        from sklearn.model_selection import train_test_split
    except ImportError as exc:
        raise RuntimeError("Install optional torch, numpy, scikit-learn dependencies") from exc
    from mechanization.far_mechanization.mechanistic_fidelity import MechanismAudit

    torch.set_num_threads(1)
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    torch.use_deterministic_algorithms(True)
    registered = datetime.now(timezone.utc).isoformat()

    digits = load_digits()
    raw = digits.data.astype(np.float32)
    images = raw / 16.0
    labels = digits.target.astype(np.int64)
    train_ids, test_ids = train_test_split(
        np.arange(len(images)), test_size=0.30,
        stratify=labels, random_state=SEED,
    )

    class Network(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = torch.nn.Linear(64, 24)
            self.fc2 = torch.nn.Linear(24, 10)

        def forward(self, inputs, unit=0, replacement=None):
            hidden = torch.relu(self.fc1(inputs))
            if replacement is not None:
                hidden = hidden.clone()
                hidden[:, unit] = replacement
            return self.fc2(hidden), hidden

    net = Network()
    optimizer = torch.optim.Adam(net.parameters(), lr=0.01)
    train_x = torch.from_numpy(images[train_ids])
    train_y = torch.from_numpy(labels[train_ids])
    for _ in range(60):
        net.train()
        optimizer.zero_grad()
        logits, _ = net(train_x)
        loss = torch.nn.functional.cross_entropy(logits, train_y)
        loss.backward()
        optimizer.step()
    net.eval()
    with torch.no_grad():
        training_hidden = torch.relu(net.fc1(train_x)).numpy()
        predictions = net(torch.from_numpy(images[test_ids]))[0].argmax(1).numpy()
        test_accuracy = float(np.mean(predictions == labels[test_ids]))
        output_weights = net.fc2.weight.detach().numpy()

    # Select neuron and one-pixel explanation using TRAIN data exclusively.
    best = None
    for unit in range(training_hidden.shape[1]):
        activation = training_hidden[:, unit]
        if activation.std() < 0.04:
            continue
        options = []
        for pixel in range(64):
            column = images[train_ids, pixel]
            if column.std() < 0.03:
                continue
            correlation = abs(np.corrcoef(column, activation)[0, 1])
            options.append((correlation, pixel))
        if not options:
            continue
        correlation, pixel = max(options)
        influence = float(np.std(activation) * np.linalg.norm(output_weights[:, unit]))
        candidate = (influence * (0.35 + correlation), unit, pixel, correlation)
        if best is None or candidate[0] > best[0]:
            best = candidate
    _, unit, pixel, correlation = best
    activations = training_hidden[:, unit]
    train_pixel = images[train_ids, pixel]
    alpha = float(np.dot(train_pixel - train_pixel.mean(), activations - activations.mean())
                  / np.dot(train_pixel - train_pixel.mean(), train_pixel - train_pixel.mean()))
    beta = float(activations.mean() - alpha * train_pixel.mean())
    baseline = float(activations.mean())

    def probability_vector(logits):
        values = np.asarray(logits, dtype=np.float64) / 2
        exp = np.exp(values - values.max())
        probabilities = 0.995 * (exp / exp.sum()) + 0.005 / len(exp)
        units = np.floor(probabilities * MICRO).astype(int)
        missing = MICRO - int(units.sum())
        fractions = probabilities * MICRO - units
        if missing > 0:
            order = sorted(range(len(units)), key=lambda j: (-fractions[j], j))
            for j in order[:missing]:
                units[j] += 1
        elif missing < 0:
            order = sorted(range(len(units)), key=lambda j: (fractions[j], j))
            for j in order[:abs(missing)]:
                units[j] -= 1
        assert min(units) > 0 and int(units.sum()) == MICRO
        return [f"{int(v)//MICRO}.{int(v)%MICRO:06d}" for v in units]

    def measure(index, split, identity=False):
        vector = images[index].astype(np.float32)
        with torch.no_grad():
            input_tensor = torch.from_numpy(vector[None, :])
            original_logits, original_hidden = net(input_tensor)
            observed = float(original_hidden[0, unit])
            explained = (observed if identity else
                         max(0.0, float(alpha * vector[pixel] + beta)))
            replaced_logits, _ = net(
                input_tensor, unit=unit,
                replacement=torch.tensor([explained], dtype=torch.float32))
            baseline_logits, _ = net(
                input_tensor, unit=unit,
                replacement=torch.tensor([baseline], dtype=torch.float32))
        return {
            "id": f"digits-{int(index)}",
            "split": split,
            "input_sha256": _sha(vector.tobytes()),
            "measured_at": datetime.now(timezone.utc).isoformat(),
            "source_ids": ["training-run"],
            "observed_activation": f"{observed:.6f}",
            "explained_activation": f"{explained:.6f}",
            "baseline_activation": f"{baseline:.6f}",
            "original_probs": probability_vector(original_logits.numpy()[0]),
            "replacement_probs": probability_vector(replaced_logits.numpy()[0]),
            "baseline_probs": probability_vector(baseline_logits.numpy()[0]),
        }

    def kl(p, q):
        pp = np.asarray([float(x) for x in p])
        qq = np.asarray([float(x) for x in q])
        return float(np.sum(pp * np.log(pp / qq)))

    test_ids = list(map(int, test_ids))
    heldout = [measure(i, "heldout") for i in test_ids[:16]]
    candidates = [measure(i, "adversarial") for i in test_ids[16:170]]
    candidates.sort(key=lambda row: (
        -(kl(row["original_probs"], row["replacement_probs"])
          - kl(row["original_probs"], row["baseline_probs"])),
        row["id"],
    ))
    adversarial = candidates[:8]
    controls = [measure(i, "control", identity=True) for i in test_ids[170:178]]

    log = json.dumps({
        "dataset": "sklearn.datasets.load_digits",
        "dataset_sha256": _sha(raw.tobytes()),
        "train_rows": len(train_ids), "test_rows": len(test_ids),
        "training_seed": SEED, "train_epochs": 60, "hidden_layer_width": 24,
        "heldout_selection": "first 16 seeded test indices",
        "adversarial_selection": "largest KL delta from disjoint 154-case test pool (selection-biased exploratory negatives)",
        "control_selection": "next disjoint 8 test indices",
        "score_smoothing": "softmax(logits/2) mixed with 0.5% uniform",
        "component_unit": int(unit), "single_pixel_predictor": int(pixel),
        "registration_claimed_at": registered,
        "note": "Real trained neural network, NOT a language model or independent scientific replication.",
    }, sort_keys=True)

    state = {name: [float(x) for x in tensor.detach().numpy().flatten()]
             for name, tensor in net.state_dict().items()}
    shapes = {name: list(tensor.shape)
              for name, tensor in net.state_dict().items()}
    sample_ids = list(test_ids[:16]) + [
        int(row["id"].split("-")[1]) for row in adversarial
    ] + list(test_ids[170:178])
    checkpoint = {
        "format_version": "FAR-MECH-DIGITS-CHECKPOINT/0.1",
        "dataset_sha256": _sha(raw.tobytes()),
        "seed": SEED,
        "indices_train": list(map(int, train_ids)),
        "hidden_unit": int(unit), "selected_pixel": int(pixel),
        "alpha": alpha, "beta": beta, "baseline": baseline,
        "weights": state, "shapes": shapes,
        "cases": {str(i): [float(x) for x in images[i]] for i in sample_ids},
    }
    checkpoint_hash = _sha(_canonical(checkpoint))
    document = {
        "format_version": "FAR-MECH/0.1",
        "status": "Research",
        "id": "digits-mlp-interventions-" + registered[:10],
        "data_class": "submitted_experiment",
        "registered_at": registered,
        "model": {
            "artifact_sha256": checkpoint_hash,
            "component_id": f"fc1.relu.{unit}",
            "intervention_type": "single_component_activation_replacement",
            "reference_population_sha256": _sha(_canonical(list(map(int, train_ids)))),
            "execution_contract": {
                "deterministic": True,
                "same_nonintervened_state": True,
                "exact_output_distributions": True,
            },
        },
        "explanation": {
            "id": "single-pixel-affine-relu",
            "description": f"ReLU(alpha * normalized_pixel[{pixel}] + beta), parameters fitted only on train; neuron {unit}. Mean-activation baseline. Adversarial inputs are selected post hoc on downstream degradation.",
            "hypothesis_source_ids": ["training-run"],
        },
        "sources": [{
            "id": "training-run", "text": log,
            "sha256": _sha(log.encode("utf-8")),
        }],
        "cases": heldout + adversarial + controls,
    }
    # Fails closed if data cannot satisfy the real FAR-MECH schema.
    audit = MechanismAudit.from_dict(document)
    output.mkdir(parents=True, exist_ok=True)
    (output / "digits_mechanism_traces.json").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "digits_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "digits_mechanism_report.json").write_text(
        json.dumps(audit.evaluate(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"heldout": len(heldout), "adversarial": len(adversarial),
            "control": len(controls), "test_accuracy": test_accuracy,
            "checkpoint_sha256": checkpoint_hash,
            "component_id": document["model"]["component_id"],
            "status": "REAL_TRAINED_MODEL_SUBMITTED_INTERVENTIONS_NOT_INDEPENDENTLY_REPLAYED"}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.output), indent=2))


if __name__ == "__main__":
    main()
