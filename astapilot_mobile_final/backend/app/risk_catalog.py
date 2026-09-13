from .models import RiskCategory, Severity

RISK_CATALOG = {
    # Urban / cadastral
    "URBAN_NON_REMEDIABLE": dict(severity=Severity.C4, category=RiskCategory.URBAN_PLANNING, score_cap=25, action="TECHNICAL_LEGAL_REVIEW"),
    "DEMOLITION_RISK": dict(severity=Severity.C4, category=RiskCategory.URBAN_PLANNING, score_cap=20, action="TECHNICAL_LEGAL_REVIEW"),
    "MUNICIPAL_ACQUISITION_RISK": dict(severity=Severity.C4, category=RiskCategory.URBAN_PLANNING, score_cap=20, action="TECHNICAL_LEGAL_REVIEW"),
    "MAJOR_URBAN_DISCREPANCY": dict(severity=Severity.C3, category=RiskCategory.URBAN_PLANNING, score_cap=60, action="TECHNICAL_REVIEW"),
    "REMEDIABLE_URBAN_DISCREPANCY": dict(severity=Severity.C2, category=RiskCategory.URBAN_PLANNING, score_cap=84, action="TECHNICAL_REVIEW"),
    "MINOR_CADASTRAL_MISMATCH": dict(severity=Severity.C2, category=RiskCategory.DOCUMENTATION, score_cap=88, action="CADASTRAL_REVIEW"),
    "CADASTRAL_MISMATCH_MAJOR": dict(severity=Severity.C3, category=RiskCategory.DOCUMENTATION, score_cap=65, action="CADASTRAL_REVIEW"),
    "AGIBILITY_MISSING": dict(severity=Severity.C3, category=RiskCategory.URBAN_PLANNING, score_cap=65, action="TECHNICAL_REVIEW"),
    "HERITAGE_CONSTRAINT": dict(severity=Severity.C2, category=RiskCategory.LEGAL, score_cap=82, action="SPECIALIST_REVIEW"),
    "ARCHAEOLOGICAL_CONSTRAINT": dict(severity=Severity.C3, category=RiskCategory.LEGAL, score_cap=55, action="SPECIALIST_REVIEW"),

    # Occupancy / rights
    "TENANCY_OPPOSABLE": dict(severity=Severity.C3, category=RiskCategory.OCCUPANCY, score_cap=60, action="LEGAL_REVIEW"),
    "TENANCY_NON_OPPOSABLE": dict(severity=Severity.C2, category=RiskCategory.OCCUPANCY, score_cap=82, action="LEGAL_REVIEW"),
    "OCCUPIED_DEBTOR": dict(severity=Severity.C2, category=RiskCategory.OCCUPANCY, score_cap=82, action="POSSESSION_REVIEW"),
    "OCCUPIED_THIRD_PARTY": dict(severity=Severity.C3, category=RiskCategory.OCCUPANCY, score_cap=65, action="LEGAL_REVIEW"),
    "OCCUPANCY_UNKNOWN": dict(severity=Severity.C2, category=RiskCategory.OCCUPANCY, score_cap=80, action="VERIFY_OCCUPANCY"),
    "BARE_OWNERSHIP": dict(severity=Severity.C3, category=RiskCategory.RIGHTS, score_cap=55, action="RIGHTS_REVIEW"),
    "OWNERSHIP_SHARE": dict(severity=Severity.C3, category=RiskCategory.RIGHTS, score_cap=55, action="RIGHTS_REVIEW"),
    "USUFRUCT_ONLY": dict(severity=Severity.C3, category=RiskCategory.RIGHTS, score_cap=55, action="RIGHTS_REVIEW"),

    # Legal / condominium
    "LEGAL_DISPUTE": dict(severity=Severity.C3, category=RiskCategory.LEGAL, score_cap=55, action="LEGAL_REVIEW"),
    "CONDO_ARREARS_HIGH": dict(severity=Severity.C3, category=RiskCategory.CONDOMINIUM, score_cap=65, action="CONDOMINIUM_REVIEW"),
    "CONDO_ARREARS_PRESENT": dict(severity=Severity.C2, category=RiskCategory.CONDOMINIUM, score_cap=84, action="CONDOMINIUM_REVIEW"),
    "EASEMENT_OR_SERVITUDE": dict(severity=Severity.C2, category=RiskCategory.LEGAL, score_cap=82, action="LEGAL_REVIEW"),

    # Physical
    "STRUCTURAL_CRACKS_REPORTED": dict(severity=Severity.C3, category=RiskCategory.PHYSICAL, score_cap=65, action="STRUCTURAL_REVIEW"),
    "RENOVATION_NEEDED": dict(severity=Severity.C1, category=RiskCategory.PHYSICAL, score_cap=100, action="COST_ESTIMATE"),
    "ASBESTOS_OR_HAZARDOUS_MATERIAL": dict(severity=Severity.C3, category=RiskCategory.PHYSICAL, score_cap=60, action="SPECIALIST_REVIEW"),

    # Documentation / procedure
    "DOCUMENT_CONTRADICTION": dict(severity=Severity.C3, category=RiskCategory.DOCUMENTATION, score_cap=65, action="DOCUMENT_REVIEW"),
    "KEY_DOCUMENT_MISSING": dict(severity=Severity.C3, category=RiskCategory.DOCUMENTATION, score_cap=60, action="DOCUMENT_REVIEW"),
    "PROCEDURE_DATA_INCONSISTENT": dict(severity=Severity.C3, category=RiskCategory.PROCEDURE, score_cap=60, action="PROCEDURE_REVIEW"),
    "AUCTION_DEADLINE_CLOSE": dict(severity=Severity.C1, category=RiskCategory.PROCEDURE, score_cap=100, action="TIMELINE_REVIEW"),
    "DEPOSIT_UNCLEAR": dict(severity=Severity.C2, category=RiskCategory.PROCEDURE, score_cap=82, action="PROCEDURE_REVIEW"),
    "BALANCE_DEADLINE_UNCLEAR": dict(severity=Severity.C2, category=RiskCategory.PROCEDURE, score_cap=82, action="PROCEDURE_REVIEW"),

    # Economic / marketability
    "HIGH_REGULARIZATION_COST": dict(severity=Severity.C3, category=RiskCategory.ECONOMIC, score_cap=65, action="COST_REVIEW"),
    "MARKET_VALUE_LOW_CONFIDENCE": dict(severity=Severity.C2, category=RiskCategory.MARKETABILITY, score_cap=84, action="VALUATION_REVIEW"),
}
