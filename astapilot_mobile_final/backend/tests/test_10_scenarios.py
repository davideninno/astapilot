from app.models import *
from app.scoring import analyze_auction


def risk(code, severity, category, cap, title=None):
    return RiskFactor(code=code, severity=severity, category=category, title=title or code, description=code, score_cap=cap)


def scenario(name, scores, risks=None, status=ProcedureStatus.ACTIVE, right=OwnershipRight.FULL_OWNERSHIP, goal="BOTH", confidence=92):
    c = ConfidenceInputs(document_coverage=confidence, extraction_confidence=confidence, cross_document_consistency=confidence, data_freshness=confidence)
    return AuctionAnalysisInput(
        auction_id=name,
        title=name,
        procedure_status=status,
        ownership_right=right,
        user_goal=goal,
        component_scores=ComponentScores(**scores),
        confidence_inputs=c,
        risks=risks or [],
    )


CASES = [
    scenario("01_clean", dict(economic=88, urban_planning=100, occupancy=100, documentation=95, procedure=95, marketability=85)),
    scenario("02_remediable", dict(economic=82, urban_planning=72, occupancy=100, documentation=90, procedure=92, marketability=80), [risk("REMEDIABLE_URBAN_DISCREPANCY", Severity.C2, RiskCategory.URBAN_PLANNING, 84)]),
    scenario("03_minor_abuse_condo", dict(economic=80, urban_planning=68, occupancy=100, documentation=88, procedure=90, marketability=75), [risk("REMEDIABLE_URBAN_DISCREPANCY", Severity.C2, RiskCategory.URBAN_PLANNING, 84), risk("CONDO_ARREARS_PRESENT", Severity.C2, RiskCategory.CONDOMINIUM, 84)]),
    scenario("04_high_condo", dict(economic=74, urban_planning=90, occupancy=100, documentation=90, procedure=90, marketability=74), [risk("CONDO_ARREARS_HIGH", Severity.C3, RiskCategory.CONDOMINIUM, 65)]),
    scenario("05_opposable_lease", dict(economic=84, urban_planning=95, occupancy=35, documentation=92, procedure=92, marketability=70), [risk("TENANCY_OPPOSABLE", Severity.C3, RiskCategory.OCCUPANCY, 60)]),
    scenario("06_nonopposable_occupied", dict(economic=80, urban_planning=75, occupancy=60, documentation=90, procedure=90, marketability=76), [risk("TENANCY_NON_OPPOSABLE", Severity.C2, RiskCategory.OCCUPANCY, 82), risk("REMEDIABLE_URBAN_DISCREPANCY", Severity.C2, RiskCategory.URBAN_PLANNING, 84)]),
    scenario("07_multi_c3", dict(economic=72, urban_planning=40, occupancy=40, documentation=80, procedure=82, marketability=55), [risk("AGIBILITY_MISSING", Severity.C3, RiskCategory.URBAN_PLANNING, 65), risk("LEGAL_DISPUTE", Severity.C3, RiskCategory.LEGAL, 55), risk("ARCHAEOLOGICAL_CONSTRAINT", Severity.C3, RiskCategory.LEGAL, 55)]),
    scenario("08_nonremediable", dict(economic=95, urban_planning=0, occupancy=100, documentation=95, procedure=95, marketability=20), [risk("URBAN_NON_REMEDIABLE", Severity.C4, RiskCategory.URBAN_PLANNING, 25), risk("DEMOLITION_RISK", Severity.C4, RiskCategory.URBAN_PLANNING, 20)]),
    scenario("09_bare_ownership", dict(economic=90, urban_planning=95, occupancy=30, documentation=90, procedure=90, marketability=55), [risk("BARE_OWNERSHIP", Severity.C3, RiskCategory.RIGHTS, 55)], right=OwnershipRight.BARE_OWNERSHIP, goal="HOME"),
    scenario("10_suspended", dict(economic=95, urban_planning=95, occupancy=95, documentation=95, procedure=10, marketability=90), status=ProcedureStatus.SUSPENDED),
]


def test_10_case_stress_profiles():
    results = [analyze_auction(c) for c in CASES]
    assert results[0].profile == "STRONG"
    assert results[1].asta_score <= 84
    assert results[3].asta_score <= 65
    assert results[4].asta_score <= 60
    assert results[6].asta_score <= 49
    assert results[7].asta_score <= 20 and results[7].profile == "CRITICAL"
    assert results[8].profile == "BLOCKED"
    assert results[9].profile == "BLOCKED"
