"""Synthetic contract regression harness. NOT independent accuracy evaluation."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from engine import InvalidBundle, canonical, digest
from workflow import investigate
from independent_check import check_report, IndependentCheckError
from bounded_io import read_bounded


def evaluate_cases(cases: list[dict]) -> dict:
    if not isinstance(cases,list) or not 1 <= len(cases) <= 100:
        raise InvalidBundle("synthetic case list requires 1-100 cases")
    records=[]
    for case in cases:
        if not isinstance(case,dict) or not isinstance(case.get("config"),dict):
            raise InvalidBundle("invalid diagnostic case")
        result=investigate(case["config"])
        expected=case.get("expected",{})
        if not isinstance(expected,dict):raise InvalidBundle("expected result must be a mapping")
        got={"claims":len(result["bundle"]["claims"]),
             "argument_statuses":[x["formal_inference"]["status"] for x in result["audit"]["interpretations"]],
             "all_claim_evidence_not_established":all(x["status"]=="NOT_ESTABLISHED" for x in result["audit"]["claims"].values()),
             "semantic_fidelity_verified":result["manifest"]["semantic_mapping_independently_verified"],
             "source_temporal_status":result["audit"]["source_temporal_status"],
             "independent_algorithm_agrees":check_report(result["bundle"],result["audit"])["independent_algorithm_agrees"]}
        matches={k:got.get(k)==v for k,v in expected.items()}
        records.append({"case_id":case.get("case_id"),"checks":matches,"passed":all(matches.values()),
                        "result":got,"input_sha256":result["audit"]["input_sha256"]})
    return {"schema":"far-synthetic-contract-diagnostic/1.0",
            "case_count":len(records),"passed_count":sum(x["passed"] for x in records),
            "records":records,"external_accuracy":None,
            "scope":"Project-authored synthetic software regression, not independently adjudicated field performance"}


def main()->int:
    p=argparse.ArgumentParser(description="Run synthetic, internal FAR pipeline contract tests")
    p.add_argument("cases",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    try:
        raw=read_bounded(args.cases, 500_000)
        if len(raw)>500_000:raise InvalidBundle("diagnostic case file too large")
        cases=json.loads(raw)
        result=evaluate_cases(cases)
        output=canonical(result)+b"\n"
        if args.output:args.output.write_bytes(output)
        else:sys.stdout.buffer.write(output)
        return 0 if result["passed_count"]==result["case_count"] else 1
    except (OSError,ValueError,TypeError,IndependentCheckError,RecursionError) as exc:
        print("FAR_DIAGNOSTIC_INVALID: "+str(exc),file=sys.stderr)
        return 2


if __name__=="__main__":raise SystemExit(main())
