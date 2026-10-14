#!/usr/bin/env python3
"""Keep a code-identity report and a gas rehearsal from being joined by address alone."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path.cwd().resolve()

def load(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT) or path.stat().st_size > 100_000:
        raise ValueError("input must be a small file inside the workspace")
    with path.open() as handle:
        return json.load(handle)

def align(code, gas):
    if code.get("schema") != "code-target-proofs-result-v1":
        raise ValueError("not a Code Target Proofs result")
    if gas.get("schema") != "gas-lens-v1":
        raise ValueError("not a Gas Lens report")
    code_block, gas_block = code.get("code_block"), gas.get("block")
    source, call = code.get("source_target"), gas.get("call")
    if not isinstance(code_block, dict) or not isinstance(gas_block, dict) or not isinstance(call, dict):
        raise ValueError("missing required context")
    same = (code.get("chain_id") == gas.get("chain_id") and source == call.get("to")
            and code_block.get("number") == gas_block.get("number")
            and code_block.get("hash") == gas_block.get("hash"))
    return {"schema": "evidence-alignment-v1", "status": "aligned" if same else "not_aligned",
            "chain_id": {"code": code.get("chain_id"), "gas": gas.get("chain_id")},
            "target": {"code": source, "gas": call.get("to")},
            "block": {"code": code_block, "gas": gas_block}, "gas_verdict": gas.get("verdict"),
            "code_decision": code.get("decision"),
            "scope": "Alignment only: this neither authenticates either report nor proves code behavior, call success, gas sufficiency, authority, safety, or future execution."}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("code", nargs="?", default="line-3/tools/code-target-proofs/demo-result.json")
    parser.add_argument("gas", nargs="?", default="shared/evidence-alignment/zto-gas-report.json")
    args = parser.parse_args()
    try:
        code = load(args.code)
        if "results" in code:
            code = next(item["result"] for item in code["results"] if item["token"] == "ZTO")
        print(json.dumps(align(code, load(args.gas)), indent=2))
    except (OSError, ValueError, KeyError, StopIteration, json.JSONDecodeError) as error:
        print(json.dumps({"status": "invalid", "error": str(error)}), file=sys.stderr)
        raise SystemExit(2)

if __name__ == "__main__":
    main()
