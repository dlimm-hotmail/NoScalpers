from typing import List, Dict
from src.types import Agent


def run_secondary_market(scalpers: List[Agent], consumers: List[Agent],
                         cfg: dict) -> Dict[str, float]:
    """Match scalper asking prices to consumer desperation prices.
    Returns realized markup revenue and transactions per SKU."""
    sku_prices = cfg["sku_prices"]
    # Build scalper offers: (sku, ask_price)
    offers: Dict[str, List[float]] = {}
    for a in scalpers:
        for sku, qty in a.items_purchased.items():
            ask = sku_prices[sku] * (1 + a.markup)
            offers.setdefault(sku, []).extend([ask] * qty)
    # Build consumer wants: (sku, desperation_price)
    wants: Dict[str, List[float]] = {}
    for a in consumers:
        for sku, want in a.desired.items():
            got = a.items_purchased.get(sku, 0)
            short = want - got
            if short <= 0:
                continue
            dprice = a.desperation_price.get(sku, 0.0)
            wants.setdefault(sku, []).extend([dprice] * short)
    # Greedy match: lowest ask to highest willingness.
    revenue = 0.0
    txns = 0
    for sku in set(offers) & set(wants):
        asks = sorted(offers[sku])
        bids = sorted(wants[sku], reverse=True)
        i = 0
        for bid in bids:
            if i < len(asks) and bid >= asks[i]:
                revenue += asks[i]
                txns += 1
                i += 1
    return {"secondary_revenue": revenue,
            "secondary_transactions": txns,
            "secondary_skus_matched": len(set(offers) & set(wants))}