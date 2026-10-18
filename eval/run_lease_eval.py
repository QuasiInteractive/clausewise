"""Score the lease checker on the planted-term leases (calls Claude; costs a few cents).

    uv run python eval/make_leases.py      # once
    uv run python eval/run_lease_eval.py

caught      = planted problem terms given an accepted verdict
false alarm = harmless terms called "likely_unlawful"
"""

import json
import sys
from pathlib import Path

from clausewise.lease.check import check_lease


def norm(text: str) -> str:
    return " ".join(text.split()).lower()


def main() -> int:
    golden = json.loads(Path("eval/lease_golden.json").read_text(encoding="utf-8"))
    caught = problems = false_alarms = harmless = 0
    bond_ok = 0
    for name, expected in golden.items():
        report = check_lease(Path(f"eval/leases/{name}.pdf").read_bytes())
        by_text = {norm(f.clause): f for f in report.clause_findings}
        bond = next((f for f in report.rule_findings if f.title == "Bond amount"), None)
        bond_ok += bond is not None and bond.verdict == expected["bond_verdict"]
        print(f"\n{name}: bond {bond.verdict if bond else 'missing'} "
              f"(expected {expected['bond_verdict']})")
        for term in expected["terms"]:
            finding = by_text.get(norm(term["text"]))
            verdict = finding.verdict if finding else "missing"
            is_problem = "likely_unlawful" in term["accept"]
            if is_problem:
                problems += 1
                caught += verdict in term["accept"]
            else:
                harmless += 1
                false_alarms += verdict == "likely_unlawful"
            mark = "PASS" if (verdict in term["accept"] if is_problem
                              else verdict != "likely_unlawful") else "FAIL"
            print(f"  {mark} {term['key']:9} {verdict:16} accepts {term['accept']}")
    print(f"\nproblems caught {caught}/{problems} · false alarms {false_alarms}/{harmless}"
          f" · bond rule {bond_ok}/{len(golden)}")
    return 0 if caught == problems and false_alarms == 0 and bond_ok == len(golden) else 1


if __name__ == "__main__":
    sys.exit(main())
