"""A deliberately clean target for the enshittify.dev demo."""

DEFAULT_TAX_RATE = 0.18


def calculate_order_total(
    prices: list[float], tax_rate: float = DEFAULT_TAX_RATE
) -> float:
    subtotal = sum(prices)
    tax_amount = subtotal * tax_rate
    final_total = subtotal + tax_amount
    return round(final_total, 2)


def format_order_summary(customer_name: str, total: float) -> str:
    """Return a compact, readable order summary."""
    if total > 0:
        return f"{customer_name}: {total:.2f}"
    return f"{customer_name}: no charge"
