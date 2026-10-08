"""Red-Team Mode: the firing range.

Loads redteam/attacks.json, fires each attack through the real pipeline
(extract -> evidence -> classify -> validate), and scores whether the
defense held: verdict matches expected AND nothing in must_not_leak
appears in the stamped verdict.

Sender history is snapshotted and restored around the run so the battery
stays repeatable — the range leaves no footprints.
"""
import json
import os
import shutil

from .extractor import extract
from .evidence import collect_evidence
from .classifier import classify
from .validator import validate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATTERY = os.path.join(ROOT, "redteam", "attacks.json")
HISTORY = os.path.join(ROOT, "sender_history.json")


def run_attack(attack):
    email = extract(attack["raw_email"])
    evidence = collect_evidence(email)
    verdict = validate(
        classify(email, evidence),
        lambda: classify(email, evidence),
        evidence,
    )
    blob = json.dumps(verdict.model_dump()).lower()
    leaked = [s for s in attack.get("must_not_leak", []) if s.lower() in blob]
    held = (verdict.verdict == attack["expected_verdict"]) and not leaked
    return verdict, held, leaked


def main():
    attacks = json.load(open(BATTERY))
    backup = None
    if os.path.exists(HISTORY):
        backup = HISTORY + ".redteam-bak"
        shutil.copy(HISTORY, backup)
    results = []
    try:
        for a in attacks:
            try:
                verdict, held, leaked = run_attack(a)
                results.append((a, verdict.verdict, held, leaked, None))
            except Exception as e:  # a crash is a finding too
                results.append((a, "ERROR", False, [], str(e)))
    finally:
        if backup:
            shutil.move(backup, HISTORY)
        elif os.path.exists(HISTORY):
            os.remove(HISTORY)  # the battery created it; leave no trace

    held_n = 0
    cats = {}
    for a, got, held, leaked, err in results:
        mark = "HELD" if held else "BREACHED"
        held_n += held
        c = cats.setdefault(a["category"], [0, 0])
        c[1] += 1
        c[0] += held
        extra = ""
        if leaked:
            extra = f" | LEAKED: {leaked}"
        if err:
            extra = f" | ERROR: {err}"
        print(f"[{mark}] {a['id']} {a['name']} (expected {a['expected_verdict']}, got {got}){extra}")
    print(f"\nScoreboard: {held_n}/{len(results)} held")
    for cat, (h, t) in cats.items():
        print(f"  {cat}: {h}/{t}")


if __name__ == "__main__":
    main()
