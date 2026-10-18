import io
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from clausewise.lease.check import parse_verdict
from clausewise.lease.clauses import clauses_to_check, split_clauses
from clausewise.lease.extract import LeaseDoc, ScannedPdfError, read_lease
from clausewise.lease.rules import bond_rule, weekly_rent
from clausewise.retrieve import Hit

FORM = Path(__file__).parent.parent / "data" / "forms" / "form18a.pdf"


def filled_form(values: dict[str, str]) -> bytes:
    writer = PdfWriter(clone_from=PdfReader(FORM))
    for page in writer.pages:
        if page.get("/Annots"):
            writer.update_page_form_field_values(page, values, auto_regenerate=False)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_filled_form_fields_are_read_even_though_they_are_not_page_text():
    pdf = filled_form({"Rent amount": "650", "week, fortnight or month": "week",
                       "Special terms": "1. No smoking inside.\n2. Tenant mows the lawn."})
    doc = read_lease(pdf)
    assert doc.is_form_18a
    assert doc.fields["Rent amount"] == "650"
    assert clauses_to_check(doc) == ["No smoking inside.", "Tenant mows the lawn."]


def test_blank_pdf_is_reported_as_a_scan():
    writer = PdfWriter()
    writer.add_blank_page(595, 842)
    buf = io.BytesIO()
    writer.write(buf)
    with pytest.raises(ScannedPdfError):
        read_lease(buf.getvalue())


def test_split_numbered_clauses_keeps_sub_items_with_their_clause():
    text = "1. The tenant must\n(a) keep it clean; and\n(b) mow.\n2) Rent is weekly.\n3 Pets ok."
    assert split_clauses(text) == [
        "The tenant must (a) keep it clean; and (b) mow.", "Rent is weekly.", "Pets ok."]


def test_split_unnumbered_lines():
    assert split_clauses("No smoking.\nBins out weekly.") == ["No smoking.", "Bins out weekly."]


@pytest.mark.parametrize(("rent", "period", "weekly"),
                         [("650", "week", 650), ("$1,300", "fortnight", 650),
                          ("2800", "month", 2800 * 12 / 52), ("650", "", None)])
def test_weekly_rent(rent, period, weekly):
    doc = LeaseDoc("x", {"Rent amount": rent, "week, fortnight or month": period})
    assert weekly_rent(doc) == pytest.approx(weekly) if weekly else weekly_rent(doc) is None


def test_bond_rule_four_weeks():
    base = {"Rent amount": "650", "week, fortnight or month": "week"}
    assert bond_rule(LeaseDoc("x", {**base, "Rental bond amount": "2600"})).verdict == "ok"
    over = bond_rule(LeaseDoc("x", {**base, "Rental bond amount": "$3,900"}))
    assert over.verdict == "likely_unlawful" and "sec.112" in over.citations[0][1]
    assert bond_rule(LeaseDoc("x", base)) is None  # no bond stated: no finding, no guess


def _hits(n: int) -> list[Hit]:
    return [Hit(i, "s", "u", f"sec.{i}", f"s {i}", "b", "residential", 0.0) for i in range(1, n + 1)]


def test_parse_verdict_accepts_a_cited_judgement():
    f = parse_verdict('{"verdict": "likely_unlawful", "reason": "No.", "cites": [2, 2, 1]}',
                      "c", _hits(3))
    assert f.verdict == "likely_unlawful" and [h.anchor for h in f.sources] == ["sec.2", "sec.1"]


@pytest.mark.parametrize("raw", [
    "not json at all",
    '{"verdict": "likely_unlawful", "reason": "No.", "cites": []}',      # uncited
    '{"verdict": "likely_unlawful", "reason": "No.", "cites": [9]}',     # unsupplied source
    '{"verdict": "illegal", "reason": "No.", "cites": [1]}',             # unknown verdict
])
def test_parse_verdict_downgrades_anything_unsupported(raw):
    assert parse_verdict(raw, "c", _hits(3)).verdict == "not_covered"
