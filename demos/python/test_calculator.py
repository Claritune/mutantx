"""Tests for the calculator module.

These tests deliberately have gaps to demonstrate mutation testing value:
- No tests for percentage() at all
- No edge-case tests for division by zero
- No boundary tests for apply_discount (0%, 100%, negative, >100%)
- No tests for compound_interest with zero principal or zero rate
- No tests for split_bill with zero tip or minimum people
"""

import pytest
from calculator import (
    add,
    subtract,
    multiply,
    divide,
    apply_discount,
    compound_interest,
    split_bill,
)


# --- Basic arithmetic (happy path only) ---

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0


def test_subtract():
    assert subtract(10, 4) == 6
    assert subtract(0, 5) == -5


def test_multiply():
    assert multiply(3, 7) == 21
    assert multiply(-2, 4) == -8


def test_divide():
    assert divide(10, 2) == 5.0
    assert divide(7, 2) == 3.5


# --- Discount (happy path, no boundaries) ---

def test_apply_discount_normal():
    assert apply_discount(100, 20) == 80.0
    assert apply_discount(50, 10) == 45.0


# --- Compound interest (one normal case) ---

def test_compound_interest_normal():
    result = compound_interest(1000, 0.05, 1, 12)
    assert round(result, 2) == 1051.16


# --- Bill splitting (one normal case) ---

def test_split_bill_normal():
    result = split_bill(100, 4, 20)
    assert result == 30.0
