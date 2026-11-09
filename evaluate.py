"""Evaluate baseline and router on the same labeled cases."""
import argparse
import json
import math
import os
from pathlib import Path

from router import PRICE_CHECKED, PRICES, demo_provider, groq, load_cases, run


def summarize(rows, mode):
    attempts = [attempt for row in rows for attempt in row["attempts"]]
    passed = sum(row["passed"] for row in rows)
    known = math.fsum(attempt["estimated_usd"] for attempt in attempts if attempt["estimated_usd"] is not None)
    unknown = sum(attempt["estimated_usd"] is None for attempt in attempts)
    latencies = sorted(row["latency_ms"] for row in rows if row["latency_ms"] is not None)
    return {
        "cases": len(rows), "passed": passed, "pass_rate": passed / len(rows),
        "request_failures": sum(not row["ok"] for row in rows),
        "fallbacks": sum(row["fallback_used"] for row in rows),
        "provider_attempts": len(attempts),
        "p95_latency_ms": latencies[math.ceil(0.95 * len(latencies)) - 1] if mode == "live" and latencies else None,
        "known_usage_cost_usd": round(known, 10),
        "attempts_without_cost": unknown,
        "estimated_usd_per_pass": round(known / passed, 10) if passed and not unknown else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("demo", "live"), default="demo")
    parser.add_argument("--split", choices=("dev", "test"), default="test")
    parser.add_argument("--case", help="Evaluate only this case ID in the selected split.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "live" and not os.environ.get("GROQ_API_KEY", "").strip():
        parser.error("Set GROQ_API_KEY first.")
    all_cases = load_cases()
    cases = [case for case in all_cases if case["split"] == args.split and (not args.case or case["id"] == args.case)]
    if not cases:
        parser.error("No case matches the selected split and ID.")
    provider = demo_provider(all_cases) if args.mode == "demo" else groq
    groups = {"baseline": [], "router": []}
    for index, case in enumerate(cases):
        strategies = ("baseline", "router") if index % 2 == 0 else ("router", "baseline")
        for strategy in strategies:
            result = run(case["task"], case["text"], strategy, provider)
            passed = result["ok"] and result["value"] == case["expected"]
            if args.mode == "demo":
                result["latency_ms"] = None
            groups[strategy].append({"id": case["id"], "task": case["task"],
                                     "expected": case["expected"], "passed": passed, **result})
    summary = {strategy: summarize(rows, args.mode) for strategy, rows in groups.items()}
    report = {"mode": args.mode, "split": args.split, "price_checked": PRICE_CHECKED,
              "price_usd_per_million_tokens": PRICES, "summary": summary, "results": groups}
    suffix = f"-{args.case}" if args.case else ""
    output = args.output or Path("reports") / f"{args.mode}-{args.split}{suffix}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Report: {output}")


if __name__ == "__main__":
    main()
