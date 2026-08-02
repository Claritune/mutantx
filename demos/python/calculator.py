"""Calculator module with arithmetic, financial, and utility functions."""


def add(a: float, b: float) -> float:
    """Return the sum of two numbers."""
    return a + b


def subtract(a: float, b: float) -> float:
    """Return the difference of two numbers."""
    return a - b


def multiply(a: float, b: float) -> float:
    """Return the product of two numbers."""
    return a * b


def divide(a: float, b: float) -> float:
    """Return the quotient of two numbers.

    Raises:
        ZeroDivisionError: If b is zero.
    """
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b


def percentage(value: float, total: float) -> float:
    """Return what percentage `value` is of `total`.

    Raises:
        ZeroDivisionError: If total is zero.
    """
    if total == 0:
        raise ZeroDivisionError("Total cannot be zero")
    return (value / total) * 100


def apply_discount(price: float, discount_pct: float) -> float:
    """Apply a discount percentage to a price and return the final price.

    Args:
        price: Original price (must be non-negative).
        discount_pct: Discount percentage between 0 and 100 inclusive.

    Raises:
        ValueError: If price is negative or discount is out of range.
    """
    if price < 0:
        raise ValueError("Price cannot be negative")
    if discount_pct < 0 or discount_pct > 100:
        raise ValueError("Discount must be between 0 and 100")
    return price * (1 - discount_pct / 100)


def compound_interest(
    principal: float, rate: float, years: int, n: int = 12
) -> float:
    """Calculate compound interest.

    Args:
        principal: Initial investment amount (must be non-negative).
        rate: Annual interest rate as a decimal (e.g. 0.05 for 5%).
        years: Number of years.
        n: Compounding frequency per year (default: 12 for monthly).

    Raises:
        ValueError: If principal is negative, years is negative, or n < 1.
    """
    if principal < 0:
        raise ValueError("Principal cannot be negative")
    if years < 0:
        raise ValueError("Years cannot be negative")
    if n < 1:
        raise ValueError("Compounding frequency must be at least 1")
    return principal * (1 + rate / n) ** (n * years)


def split_bill(total: float, people: int, tip_pct: float = 15.0) -> float:
    """Split a bill among people, including a tip.

    Args:
        total: Bill total (must be non-negative).
        people: Number of people (must be at least 1).
        tip_pct: Tip percentage (must be non-negative).

    Raises:
        ValueError: If total is negative, people < 1, or tip is negative.
    """
    if total < 0:
        raise ValueError("Total cannot be negative")
    if people < 1:
        raise ValueError("Need at least one person")
    if tip_pct < 0:
        raise ValueError("Tip cannot be negative")
    total_with_tip = total * (1 + tip_pct / 100)
    return round(total_with_tip / people, 2)
