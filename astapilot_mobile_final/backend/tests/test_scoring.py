from app.models import (
    AuctionAnalysisInput, ComponentScores, ConfidenceInputs, RiskFactor,
    RiskCategory, Severity, ProcedureStatus, OwnershipRight
)
from app.scoring import analyze_auction


def base_input(**overrides):
    data = dict(
        auction_id="A1",
        title="Test auction",
        procedure_status=ProcedureStatus.ACTIVE,
        ownership_right=OwnershipRight.FULL_OWNERSHIP,
        user_goal="BOTH",
        component_scores=ComponentScores(
            economic=90, urban_planning=90, occupancy=90,
            documentation=90, procedure=90, marketability=90,
        ),
        confidence_inputs=ConfidenceInputs(
            document_coverage=95,
            extraction_confidence=95,
            cross_document_consistency=95,
            data_freshness=95,
        ),
        risks=[],
    )
    data.update(overrides)
    return AuctionAnalysisInput(**data)


def risk(code, sev, cap=None):
    return RiskFactor(
        code=code,
        severity=sev,
        category=RiskCategory.URBAN_PLANNING,
        title=code,
        description=code,
        score_cap=cap,
    )


def test_clean_case_scores_high():
    r = analyze_auction(base_input())
    assert r.asta_score == 90
    assert r.profile == "STRONG"


def test_c4_caps_score_at_25():
    r = analyze_auction(base_input(risks=[risk("URBAN_NON_REMEDIABLE", Severity.C4)]))
    assert r.asta_score == 25
    assert r.profile == "CRITICAL"


def test_two_c3_cap_score_at_49():
    r = analyze_auction(base_input(risks=[risk("LEASE_OPPOSABLE", Severity.C3), risk("LEGAL_DISPUTE", Severity.C3)]))
    assert r.asta_score == 49
    assert r.profile == "HIGH_RISK"


def test_suspended_procedure_blocks():
    r = analyze_auction(base_input(procedure_status=ProcedureStatus.SUSPENDED))
    assert r.asta_score is None
    assert r.profile == "BLOCKED"


def test_bare_ownership_blocks_home_goal():
    r = analyze_auction(base_input(ownership_right=OwnershipRight.BARE_OWNERSHIP, user_goal="HOME"))
    assert r.asta_score is None
    assert r.profile == "BLOCKED"


def test_low_confidence_profile_is_preliminary_when_score_not_critical():
    low_conf = ConfidenceInputs(
        document_coverage=30,
        extraction_confidence=40,
        cross_document_consistency=40,
        data_freshness=50,
    )
    r = analyze_auction(base_input(confidence_inputs=low_conf))
    assert r.confidence_score < 50
    assert r.profile == "PRELIMINARY"
