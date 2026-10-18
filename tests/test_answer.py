import pytest

from clausewise.answer import NOT_COVERED, NOT_COVERED_MESSAGE, check_answer
from clausewise.retrieve import Hit


def hit(n: int) -> Hit:
    return Hit(n, "src", "https://example", f"sec.{n}", f"s {n}", "body", "residential", 1.0)


HITS = [hit(1), hit(2), hit(3)]


def test_refusal_marker_becomes_friendly_message():
    a = check_answer(NOT_COVERED, HITS)
    assert not a.covered and a.text == NOT_COVERED_MESSAGE and a.sources == []


def test_answer_without_citations_is_treated_as_refusal():
    a = check_answer("Yes, landlords can always do that.", HITS)
    assert not a.covered


def test_citations_are_renumbered_to_the_sources_actually_used():
    a = check_answer("Rent can rise once a year [3]. Notice is two months [3][1].", HITS)
    assert a.covered
    assert a.text == "Rent can rise once a year [1]. Notice is two months [1][2]."
    assert [h.anchor for h in a.sources] == ["sec.3", "sec.1"]


def test_citing_a_source_that_was_not_supplied_fails():
    with pytest.raises(ValueError):
        check_answer("Something [4].", HITS)
