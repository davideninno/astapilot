from __future__ import annotations
from pydantic import BaseModel, Field


class SimulationInput(BaseModel):
    bid: float = Field(gt=0)
    conservative_market_value: float = Field(gt=0)
    taxes: float = Field(default=0, ge=0)
    renovation_cost: float = Field(default=0, ge=0)
    regularization_cost: float = Field(default=0, ge=0)
    condominium_cost: float = Field(default=0, ge=0)
    professional_cost: float = Field(default=0, ge=0)
    other_costs: float = Field(default=0, ge=0)
    contingency_rate: float = Field(default=0.05, ge=0, le=0.50)
    required_margin_rate: float = Field(default=0.20, ge=0, le=0.80)


class SimulationResult(BaseModel):
    bid: float
    non_bid_costs: float
    contingency: float
    total_investment: float
    conservative_market_value: float
    gross_margin: float
    gross_margin_rate: float
    personal_bid_limit: float
    within_personal_limit: bool
    warning: str | None = None


def simulate(data: SimulationInput) -> SimulationResult:
    base_costs = (
        data.taxes + data.renovation_cost + data.regularization_cost +
        data.condominium_cost + data.professional_cost + data.other_costs
    )
    contingency = (data.bid + base_costs) * data.contingency_rate
    non_bid = base_costs + contingency
    total = data.bid + non_bid
    margin = data.conservative_market_value - total
    margin_rate = margin / data.conservative_market_value if data.conservative_market_value else 0

    target_profit = data.conservative_market_value * data.required_margin_rate
    # Conservative: include contingency on the non-bid costs, but do not assume a lower contingency
    # simply because the user bids less.
    max_bid = max(0.0, data.conservative_market_value - target_profit - non_bid)
    warning = None
    if total > data.conservative_market_value:
        warning = "L'investimento totale supera il valore prudenziale inserito."
    elif data.bid > max_bid:
        warning = "L'offerta supera la soglia personale coerente con il margine richiesto."

    return SimulationResult(
        bid=round(data.bid, 2), non_bid_costs=round(non_bid, 2), contingency=round(contingency, 2),
        total_investment=round(total, 2), conservative_market_value=round(data.conservative_market_value, 2),
        gross_margin=round(margin, 2), gross_margin_rate=round(margin_rate, 4),
        personal_bid_limit=round(max_bid, 2), within_personal_limit=data.bid <= max_bid,
        warning=warning,
    )
