"""Benchmark: the exam (v2 — labeled set).

Stratified sample from phishsquad-testset 3/manifest.csv
(include_in_benchmark=yes), each .eml through the real pipeline,
scored against labels. Binary mapping: phishing/bec -> phishing,
legitimate/spam -> legitimate. needs_review counts as a miss.

Labels are AI first-pass: a MISS can mean the label is wrong.
Fixed seed (7) for reproducibility.
"""
import csv
import json
import os
import random
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.extractor import extract
from app.evidence import collect_evidence
from app.classifier import classify
from app.validator import validate

ROOT = os.path.dirname(os.path.abspath(__file__))
TESTSET = os.path.join(ROOT, "phishsquad-testset 3")
MANIFEST = os.path.join(TESTSET, "manifest.csv")
HISTORY = os.path.join(ROOT, "sender_history.json")
SEED = 7


def load_sample():
    rows = [r for r in csv.DictReader(open(MANIFEST, encoding="utf-8"))
            if r["include_in_benchmark"] == "yes"]

    def pick(label, source, n):
        pool = [r for r in rows if r["label"] == label
                and r["source_category"] == source
                and r["label_confidence"] == "high"]
        if len(pool) < n:  # relax to any confidence rather than shortchange
            pool = [r for r in rows if r["label"] == label
                    and r["source_category"] == source]
        return random.sample(pool, min(n, len(pool)))

    sample = []
    sample += pick("phishing", "phishing", 20)
    sample += pick("phishing", "tricks", 10)
    sample += pick("legitimate", "legitimate", 15)
    sample += pick("spam", "spam", 10)
    sample += pick("legitimate", "tricks", 5)
    random.shuffle(sample)
    return sample


def expected(label):
    return "phishing" if label in ("phishing", "bec") else "legitimate"


def main():
    random.seed(SEED)
    sample = load_sample()
    print(f"Sampled {len(sample)} emails (seed {SEED})", flush=True)
    backup = None
    if os.path.exists(HISTORY):
        backup = HISTORY + ".bench-bak"
        shutil.copy(HISTORY, backup)
    rows = []
    try:
        for j, s in enumerate(sample, 1):
            print(f"  [{j}/{len(sample)}] {s['id']}...", flush=True)
            path = os.path.join(TESTSET, s["source_category"], s["id"] + ".eml")
            try:
                raw = open(path, encoding="utf-8", errors="replace").read()
                email = extract(raw)
                evidence = collect_evidence(email)
                v = validate(classify(email, evidence),
                             lambda: classify(email, evidence), evidence)
                rows.append({"id": s["id"], "label": s["label"],
                             "label_conf": s["label_confidence"],
                             "expected": expected(s["label"]),
                             "got": v.verdict, "conf": round(v.confidence, 2),
                             "checks": [c.check for c in evidence],
                             "error": None})
            except Exception as ex:
                rows.append({"id": s["id"], "label": s["label"],
                             "label_conf": s["label_confidence"],
                             "expected": expected(s["label"]),
                             "got": "ERROR", "conf": 0.0,
                             "checks": [], "error": str(ex)[:120]})
    finally:
        if backup:
            shutil.move(backup, HISTORY)
        elif os.path.exists(HISTORY):
            os.remove(HISTORY)

    correct = 0
    for r in rows:
        ok = r["got"] == r["expected"]
        correct += ok
        mark = "OK  " if ok else "MISS"
        print(f"[{mark}] {r['id']:22s} {r['label']:10s} -> {str(r['got']):12s} "
              f"(conf {r['conf']:.2f}) checks: {', '.join(r['checks']) or 'none'}")
    print(f"\nScore: {correct}/{len(rows)}")
    json.dump(rows, open(os.path.join(ROOT, "bench_results.json"), "w"), indent=2)
    print("Saved to bench_results.json")


if __name__ == "__main__":
    main()
