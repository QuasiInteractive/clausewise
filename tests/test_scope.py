import pytest

from clausewise.ingest.scope import act_scope, rta_scope

CH2 = "Chapter 2 Residential tenancy agreements and rooming accommodation agreements"


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (("Chapter 3 Rights and obligations of parties for residential tenancies > Part 2 General"
         " standard of the premises > s 185 Lessor’s obligations generally"), "residential"),
        (("Chapter 4 Rights and obligations of parties for rooming accommodation > Part 2 Entry to"
         " residents’ rooms > s 256 Entry"), "rooming"),
        # chapter names both, the division decides
        (f"{CH2} > Part 2 Rent > Division 1 Residential tenancy agreements > s 93 Minimum period",
         "residential"),
        (f"{CH2} > Part 2 Rent > Division 2 Rooming accommodation agreements > s 105B Minimum",
         "rooming"),
        # names both all the way down: applies to both
        ((f"{CH2} > Part 3 Rental bonds > Division 2 Payments to authority > s 111 Meaning of"
         " rental bond"), "general"),
        ("Chapter 10 Residential Tenancies Authority > Part 1 Establishment > s 450 Establishment",
         "admin"),
        ("Chapter 8 Causing nuisance in moveable dwelling parks > s 400 Application", "other"),
        ("Chapter 6 Dispute resolution > Part 1 Dispute resolution process > s 403 Application",
         "general"),
    ],
)
def test_act_scope(path, expected):
    assert act_scope(path) == expected


def test_rta_scope():
    base = "https://www.rta.qld.gov.au"
    assert rta_scope(f"{base}/during-a-tenancy/repairs/emergency-repairs") == "general"
    assert rta_scope(
        f"{base}/during-a-tenancy/living-in-the-property/entry-to-the-property/"
        "entry-in-rooming-accommodation"
    ) == "rooming"
    assert rta_scope(f"{base}/before-renting/types-of-rental-properties/retirement-villages") == (
        "other"
    )
