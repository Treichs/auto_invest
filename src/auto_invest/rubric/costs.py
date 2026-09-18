from .records import Quote

COMMISSION_PER_SHARE = 0.0035
COMMISSION_MINIMUM = 0.35
COMMISSION_CAP_OF_VALUE = 0.01


def commission_per_side(shares: int, price: float) -> float:
    if shares <= 0:
        return 0.0
    per_share = max(COMMISSION_PER_SHARE * shares, COMMISSION_MINIMUM)
    return min(per_share, COMMISSION_CAP_OF_VALUE * shares * price)


def round_trip_commission(shares: int, price: float) -> float:
    return 2 * commission_per_side(shares, price)


def spread_cost_round_trip(shares: int, quote: Quote) -> float:
    return shares * (quote.ask - quote.bid)


def total_cost_round_trip(shares: int, price: float, quote: Quote) -> float:
    return round_trip_commission(shares, price) + spread_cost_round_trip(shares, quote)
