"""Pinned pretrained-language-model causal fidelity / reasoning pilot.

Optional torch + transformers dependencies. No silent fallback to random weights.
The checkpoint revision is fixed, prompts/task cases are deterministic, and
neither the FAR Core theory nor the Orthodox worldview profile is modified.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

MODEL_ID = "HuggingFaceTB/SmolLM2-135M-Instruct"
REVISION = "12fd25f77366fa6b3b4b768ec3050bf629380bac"
SEED = 7103


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


NOUNS = (
    ("daxes", "wugs", "zims"), ("ravens", "birds", "creatures"),
    ("plims", "norks", "drets"), ("roses", "flowers", "plants"),
    ("troms", "vells", "ginks"), ("squares", "shapes", "objects"),
    ("quins", "zorks", "drams"), ("otters", "mammals", "animals"),
    ("lumes", "paxes", "vorps"), ("lilies", "blooms", "things"),
    ("nims", "salks", "ruts"), ("whales", "mammals", "creatures"),
    ("borks", "daxels", "triads"), ("willows", "trees", "plants"),
    ("mips", "narps", "tuls"), ("sparrows", "birds", "animals"),
    ("grols", "narks", "bems"), ("comets", "objects", "things"),
    ("prins", "wexes", "dorps"), ("dogs", "animals", "creatures"),
    ("rasts", "vins", "kors"), ("wolves", "mammals", "animals"),
    ("sils", "norms", "zets"), ("ducks", "birds", "creatures"),
)


def task_cases():
    output = []
    for split, count, offset in (
        ("train", 24, 0), ("heldout", 12, 7),
        ("adversarial", 12, 13), ("control", 8, 19),
    ):
        for i in range(count):
            a, b, c = NOUNS[(i + offset) % len(NOUNS)]
            valid = (i % 2 == 0)
            premises = (f"Every {a} is a {b}. Every {b} is a {c}."
                        if valid else
                        f"Every {a} is a {b}. Every {c} is a {b}.")
            question = f"Does it necessarily follow that every {a} is a {c}?"
            style = {
                "train": "Respond yes or no.",
                "heldout": "Answer only yes or no.",
                "adversarial": "Ignore plausibility; decide whether the conclusion is logically forced. Reply yes or no.",
                "control": "For this formal logic question, write yes or no.",
            }[split]
            output.append({
                "id": f"{split}-{i:02d}",
                "split": split,
                "question": premises + " " + question + " " + style,
                "gold": "yes" if valid else "no",
            })
    return output


def run(output: Path, *, model_id: str = MODEL_ID, revision: str = REVISION,
        per_split: int = 12):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from mechanization.far_mechanization.mechanistic_fidelity import MechanismAudit

    if not (2 <= per_split <= 12):
        raise ValueError("per_split must be 2..12")
    if model_id != MODEL_ID or revision != REVISION:
        raise ValueError("Unregistered model/revision; create a distinct protocol")
    torch.manual_seed(SEED)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    registration = datetime.now(timezone.utc).isoformat()
    tokenizer = AutoTokenizer.from_pretrained(
        model_id, revision=revision, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, revision=revision, trust_remote_code=False,
        torch_dtype=torch.float32).cpu().eval()
    candidates = (("yes", "no"), ("Yes", "No"), (" yes", " no"))
    answer = None
    for words in candidates:
        result = [tokenizer.encode(x, add_special_tokens=False) for x in words]
        if len(result[0]) == len(result[1]) == 1 and result[0] != result[1]:
            answer = (words, [result[0][0], result[1][0]])
            break
    if answer is None:
        raise ValueError("No distinct single-token yes/no answers")
    words, labels = answer

    # Actual Llama MLP intermediate coordinate, before down projection.
    layer = model.model.layers[0].mlp.down_proj
    items = task_cases()
    train = items[:24]
    other = [x for x in items[24:] if int(x["id"].split("-")[-1]) < per_split]
    inputs = {}
    for item in train + other:
        inputs[item["id"]] = tokenizer.apply_chat_template(
            [{"role": "user", "content": item["question"]}],
            tokenize=True, add_generation_prompt=True, return_tensors="pt")

    def forward(ids, unit=None, replacement=None):
        captured = []
        def hook(_module, args):
            active = args[0]
            captured.append(active[0, -1, :].detach().clone())
            if replacement is None:
                return None
            changed = active.clone()
            changed[0, -1, unit] = float(replacement)
            return (changed,) + args[1:]
        handle = layer.register_forward_pre_hook(hook)
        try:
            with torch.inference_mode():
                logits = model(input_ids=ids, use_cache=False).logits[0, -1, :]
        finally:
            handle.remove()
        if len(captured) != 1:
            raise RuntimeError("Activation hook did not execute once")
        return captured[0], torch.softmax(logits[labels], dim=-1).cpu().double()

    activations = torch.stack([forward(inputs[x["id"]])[0] for x in train])
    influence = activations.std(dim=0) * layer.weight.detach().float().norm(dim=0)
    unit = int(torch.argmax(influence).item())
    train_len = torch.tensor([float(inputs[x["id"]].shape[-1])
                              for x in train], dtype=torch.float64)
    target = activations[:, unit].double()
    avg = float(target.mean())
    centered = train_len - train_len.mean()
    slope = float(((centered * (target - target.mean())).sum() /
                   (centered.square().sum() + 1e-3)).item())
    intercept = float(target.mean() - slope * train_len.mean())

    def fmt(v):
        return f"{float(v):.6f}"

    def probs(p):
        val = int(round(float(p[0]) * 1_000_000))
        val = min(999999, max(1, val))
        return [f"{val/1e6:.6f}", f"{(1_000_000-val)/1e6:.6f}"]

    def kl(p, q):
        return sum(float(a) * math.log(float(a) / float(b))
                   for a, b in zip(p, q))

    measured = []
    for item in other:
        ids = inputs[item["id"]]
        activation, original = forward(ids)
        true_activation = float(activation[unit])
        predicted = slope * int(ids.shape[-1]) + intercept
        if item["split"] == "control":
            predicted = true_activation
        _, replacement = forward(ids, unit, predicted)
        _, baseline = forward(ids, unit, avg)
        row = {
            "id": item["id"], "split": item["split"],
            "input_sha256": sha(ids.numpy().tobytes()),
            "measured_at": datetime.now(timezone.utc).isoformat(),
            "source_ids": ["run-manifest"],
            "observed_activation": fmt(true_activation),
            "explained_activation": fmt(predicted),
            "baseline_activation": fmt(avg),
            "original_probs": probs(original),
            "replacement_probs": probs(replacement),
            "baseline_probs": probs(baseline),
        }
        gold = item["gold"]
        evaluation = {
            "id": item["id"], "split": item["split"], "gold": gold,
            "base_correct": (words[int(original.argmax())].lower().strip() == gold),
            "replacement_correct": (words[int(replacement.argmax())].lower().strip() == gold),
            "mean_correct": (words[int(baseline.argmax())].lower().strip() == gold),
            "base_entropy": float(-(original * original.log()).sum()),
            "explanation_kl": kl(row["original_probs"], row["replacement_probs"]),
            "mean_kl": kl(row["original_probs"], row["baseline_probs"]),
        }
        measured.append((row, evaluation))

    # Content-derived fingerprint covers the actual loaded trainable weights,
    # unlike model-id-only metadata commitments.
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode())
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    model_sha = digest.hexdigest()

    manifest = {
        "model_id": model_id, "model_revision": revision,
        "weights_sha256": model_sha, "seed": SEED,
        "task": "closed two-token yes/no entailment from simple syllogisms",
        "answer_tokens": list(words), "answer_token_ids": labels,
        "train_n": len(train), "evaluation_n": len(other),
        "component": f"layer0.mlp.down_proj.input[{unit}]",
        "selection": "training activations std multiplied by down-proj column norm",
        "explanation": "train-only one-variable regression from token count",
        "baseline": "train-only mean activation",
        "probe_slope": slope, "probe_intercept": intercept,
        "per_split": per_split,
        "control": "replace with identical measured activation",
        "heldout": "new prompt framing; predeclared deterministic task cases",
        "adversarial": "different prompt framing, not selected by observed KL",
        "note": "Exploratory pretrained LM pilot; does not audit semantic neuron interpretation or MIB performance.",
    }
    source_text = json.dumps(manifest, sort_keys=True)
    audit_doc = {
        "format_version": "FAR-MECH/0.1", "status": "Research",
        "id": "pinned-smollm2-" + registration[:10],
        "data_class": "submitted_experiment",
        "registered_at": registration,
        "model": {
            "artifact_sha256": model_sha,
            "component_id": f"layer0.downproj.in.{unit}",
            "intervention_type": "single_component_activation_replacement",
            "reference_population_sha256": sha(canonical([x["question"] for x in train])),
            "execution_contract": {
                "deterministic": True, "same_nonintervened_state": True,
                "exact_output_distributions": True,
            },
        },
        "explanation": {
            "id": "token-count-linear-probe",
            "description": "Train-only scalar activation proxy using prompt token count; not a semantic explanation.",
            "hypothesis_source_ids": ["run-manifest"],
        },
        "sources": [{"id": "run-manifest", "text": source_text,
                     "sha256": sha(source_text.encode())}],
        "cases": [row for row, _ in measured],
    }
    audit = MechanismAudit.from_dict(audit_doc).evaluate()

    summaries = {}
    for split in ("heldout", "adversarial", "control"):
        sample = [case for _, case in measured if case["split"] == split]
        n = len(sample)
        # A predetermined fixed 0.02 KL gate; matched-coverage controls.
        accept = [x for x in sample if x["explanation_kl"] <= 0.02]
        k = len(accept)
        confidence = sorted(sample, key=lambda x: (x["base_entropy"], x["id"]))[:k]
        random_control = sorted(sample, key=lambda x: sha(x["id"].encode()))[:k]
        def accepted_accuracy(rows):
            return (sum(x["base_correct"] for x in rows) / len(rows)) if rows else None
        summaries[split] = {
            "n": n,
            "model_accuracy": accepted_accuracy(sample),
            "replacement_accuracy": sum(x["replacement_correct"] for x in sample) / n,
            "mean_baseline_accuracy": sum(x["mean_correct"] for x in sample) / n,
            "fidelity_gate_accepted": k,
            "fidelity_gate_accuracy": accepted_accuracy(accept),
            "confidence_matched_accuracy": accepted_accuracy(confidence),
            "hash_matched_accuracy": accepted_accuracy(random_control),
            "explanation_kl": sum(x["explanation_kl"] for x in sample) / n,
            "baseline_kl": sum(x["mean_kl"] for x in sample) / n,
        }
    result = {
        "manifest": manifest, "mechanism_audit": audit,
        "task_accuracy_and_selective_risk": summaries,
        "individual_results": [case for _, case in measured],
        "status": "EXPLORATORY_PRETRAINED_LM_PILOT_NO_EXTERNAL_SUPERIORITY_CLAIM",
        "assurance": "ONE_MODEL_ONE_COMPONENT_NO_MIB_NO_GENERAL_RELIABILITY_PROOF",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "far_mech_pretrained_trace.json").write_text(
        json.dumps(audit_doc, indent=2, sort_keys=True) + "\n")
    (output / "far_mech_pretrained_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-split", type=int, default=12)
    arguments = parser.parse_args()
    data = run(arguments.output, per_split=arguments.per_split)
    print(json.dumps(data["task_accuracy_and_selective_risk"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
