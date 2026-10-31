"""Independent *forward-pass* replay of the pinned pretrained-LM interventions.

Reconstructs the trusted checkpoint and prompts, re-runs actual pre-down-proj
coordinate hooks, and recomputes full-vocabulary next-token KL. Distinct from
the recorded summary-consistency check; still not a third-party replication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from evaluation.run_pretrained_lm_fidelity import MODEL_ID, REVISION, task_cases
from evaluation.validate_pretrained_lm_result import verify as verify_submitted


def replay(trace_path: Path, report_path: Path, *, full_kl_atol: float = 5e-8):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM

    # Reject inconsistent source reports before touching neural computation.
    verified = verify_submitted(trace_path, report_path)
    document = json.loads(Path(trace_path).read_text(encoding="utf-8"))
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    metadata = report["manifest"]

    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID, revision=REVISION, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, revision=REVISION, trust_remote_code=False,
        torch_dtype=torch.float32).cpu().eval()
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode())
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    weightsha = digest.hexdigest()
    if weightsha != metadata["weights_sha256"] or weightsha != document["model"]["artifact_sha256"]:
        raise ValueError("loaded model weight identity not source bound")

    coordinate = metadata["component"]
    prefix = "layer0.mlp.down_proj.input["
    if not coordinate.startswith(prefix) or not coordinate.endswith("]"):
        raise ValueError("unsupported component path")
    unit = int(coordinate[len(prefix):-1])
    layer = model.model.layers[0].mlp.down_proj
    if unit < 0 or unit >= layer.weight.shape[1]:
        raise ValueError("component coordinate out of bounds")
    if document["model"]["component_id"] != f"layer0.downproj.in.{unit}":
        raise ValueError("trace coordinate inconsistent with recorded intervention")
    labels = metadata["answer_token_ids"]
    if (len(labels) != 2 or labels[0] == labels[1] or
            labels != [tokenizer.encode(w, add_special_tokens=False)[0]
                       for w in ("yes", "no")]):
        raise ValueError("answer token ids not the pinned tokenizer's yes/no")

    tasks = {x["id"]: x for x in task_cases() if x["split"] != "train"}
    recorded_metrics = {x["id"]: x for x in report["individual_results"]}

    def forward(ids, patch=None):
        capture = []
        def hook(_module, args):
            inputs = args[0]
            capture.append(float(inputs[0, -1, unit]))
            if patch is None:
                return None
            changed = inputs.clone()
            changed[0, -1, unit] = float(patch)
            return (changed,) + args[1:]
        handle = layer.register_forward_pre_hook(hook)
        try:
            with torch.inference_mode():
                output = model(input_ids=ids, use_cache=False).logits[0, -1].double()
        finally:
            handle.remove()
        if len(capture) != 1:
            raise ValueError("pre-down-projection hook did not execute once")
        return capture[0], output

    errors = []
    with torch.inference_mode():
        for case in document["cases"]:
            task = tasks[case["id"]]
            ids = tokenizer.apply_chat_template(
                [{"role": "user", "content": task["question"]}],
                tokenize=True, add_generation_prompt=True, return_tensors="pt")
            if hashlib.sha256(ids.numpy().tobytes()).hexdigest() != case["input_sha256"]:
                raise ValueError("source input tokens cannot be reproduced: " + case["id"])
            observed, original = forward(ids)
            if abs(observed - float(case["observed_activation"])) > 2e-6:
                raise ValueError("original activation mismatch")
            _, patched = forward(ids, float(case["explained_activation"]))
            _, baseline = forward(ids, float(case["baseline_activation"]))
            p_log = torch.log_softmax(original, dim=-1)
            p = p_log.exp()
            for kind, logits, field in (
                ("explanation", patched, "full_vocabulary_explanation_kl"),
                ("baseline", baseline, "full_vocabulary_mean_kl"),
            ):
                q_log = torch.log_softmax(logits, dim=-1)
                computed = max(0.0, float((p * (p_log - q_log)).sum()))
                saved = recorded_metrics[case["id"]][field]
                if not math.isfinite(computed) or abs(computed - saved) > full_kl_atol:
                    raise ValueError(f"full-vocabulary replay mismatch {case['id']} {kind}: {computed} vs {saved}")
                errors.append(abs(computed - saved))
            for key, logits in (
                ("original_probs", original),
                ("replacement_probs", patched),
                ("baseline_probs", baseline),
            ):
                binary = torch.softmax(logits[labels], dim=-1)
                measured = [float(x) for x in case[key]]
                max_error = max(abs(float(binary[i]) - measured[i]) for i in range(2))
                if max_error > 2e-6:
                    raise ValueError(f"two-token replay mismatch {case['id']} {key}")
    return {
        "status": "ACTUAL_PRETRAINED_WEIGHT_FORWARD_REPLAY_VERIFIED",
        "cases_replayed": len(document["cases"]),
        "distribution_pairs_replayed": len(errors),
        "max_absolute_full_vocabulary_kl_error": max(errors),
        "full_kl_tolerance": full_kl_atol,
        "loaded_weight_sha256": weightsha,
        "reference_result_hash": hashlib.sha256(Path(report_path).read_bytes()).hexdigest(),
        "assurance": "INDEPENDENT_CODE_PATH_SAME_MODEL_FAMILY_NO_EXTERNAL_SCIENTIFIC_REPLICATION",
        "source_validator": verified["status"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    parser.add_argument("result", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    value = replay(args.trace, args.result)
    result = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    print(result, end="")


if __name__ == "__main__":
    main()
