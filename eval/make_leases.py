"""Build sample leases by filling in the real RTA Form 18a, with planted special terms.

    uv run python eval/make_leases.py

Writes eval/leases/*.pdf and eval/lease_golden.json (which verdicts are acceptable for each
planted term). The names and addresses are made up.
"""

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter

FORM = Path("data/forms/form18a.pdf")
OUT = Path("eval/leases")

# Each planted term lists the verdicts a correct checker may give. Unlawful terms accept
# "check" too only where the rule genuinely depends on conditions.
TERMS = {
    "repairs": (("The tenant is responsible for all repairs and maintenance of the premises, "
                "including the hot water system and the roof."), ["likely_unlawful"]),
    "entry": ("The lessor or agent may enter the premises at any time without notice.",
              ["likely_unlawful"]),
    "rent6m": ("The rent will increase by $40 per week every 6 months.", ["likely_unlawful"]),
    "nopets": ("No pets are allowed at the premises under any circumstances.",
               ["likely_unlawful", "check"]),
    "carpet": (("The tenant must pay for professional carpet steam cleaning at the end of the "
               "tenancy regardless of the condition of the carpets."),
               ["likely_unlawful", "check"]),
    "bondkeep": (("If the tenant ends the tenancy early, the full bond is forfeited to the "
                 "lessor."), ["likely_unlawful", "check"]),
    "smoking": ("Smoking is not permitted inside the premises.", ["ok", "check"]),
    "lawns": ("The tenant must keep the lawns mowed and the gardens watered and weeded.",
              ["ok", "check"]),
    "bins": ("The tenant must put the wheelie bins out for collection each week.",
             ["ok", "check"]),
}

LEASES = {
    "clean": {"terms": ["smoking", "lawns", "bins"], "rent": "650", "period": "week",
              "bond": "2600"},
    "bad": {"terms": ["repairs", "entry", "rent6m", "bins"], "rent": "1300",
            "period": "fortnight", "bond": "3900"},
    "mixed": {"terms": ["nopets", "carpet", "bondkeep", "smoking", "lawns"], "rent": "2800",
              "period": "month", "bond": "2584.62"},
}
# bond limits: clean 4x650=2600 (ok), bad 4x650=2600 < 3900 (over), mixed 4x(2800*12/52)=2584.62


def build(name: str, spec: dict) -> dict:
    reader = PdfReader(FORM)
    writer = PdfWriter(clone_from=reader)
    special = "\n".join(f"{i}. {TERMS[t][0]}" for i, t in enumerate(spec["terms"], start=1))
    values = {
        "Lessor name/trading name": "Sample Property Holdings Pty Ltd",
        "Tenant 1 full name/s": "Alex Example",
        "Address of the rental premises1": "1 Example Street",
        "Address of the rental premises2": "Southport QLD",
        "Postcode": "4215",
        "Rent amount": spec["rent"],
        "week, fortnight or month": spec["period"],
        "Rental bond amount": spec["bond"],
        "Special terms": special,
    }
    for page in writer.pages:
        writer.update_page_form_field_values(page, values, auto_regenerate=False)
    writer.set_need_appearances_writer(True)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / f"{name}.pdf", "wb") as fh:
        writer.write(fh)
    return {
        "terms": [{"key": t, "text": TERMS[t][0], "accept": TERMS[t][1]} for t in spec["terms"]],
        "bond_verdict": "likely_unlawful" if name == "bad" else "ok",
    }


def main() -> None:
    golden = {name: build(name, spec) for name, spec in LEASES.items()}
    Path("eval/lease_golden.json").write_text(json.dumps(golden, indent=2), encoding="utf-8")
    print(f"wrote {len(golden)} leases to {OUT}")


if __name__ == "__main__":
    main()
