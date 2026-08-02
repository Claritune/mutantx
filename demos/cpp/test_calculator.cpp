#include "calculator.h"
#include <cassert>
#include <cmath>
#include <iostream>

static bool approx(double a, double b, double eps = 1e-9) {
    return std::fabs(a - b) < eps;
}

// --- Calculator tests ---
// Note: divide-by-zero is NOT tested.

void test_add() {
    Calculator c;
    assert(approx(c.add(2, 3), 5));
    assert(approx(c.add(-1, 1), 0));
}

void test_subtract() {
    Calculator c;
    assert(approx(c.subtract(10, 4), 6));
    assert(approx(c.subtract(0, 0), 0));
}

void test_multiply() {
    Calculator c;
    assert(approx(c.multiply(3, 7), 21));
    assert(approx(c.multiply(-2, 5), -10));
}

void test_divide() {
    Calculator c;
    assert(approx(c.divide(10, 2), 5));
    assert(approx(c.divide(7, 2), 3.5));
    // GAP: no test for divide-by-zero exception
}

// --- fibonacci tests ---
// GAP: does NOT test fib(0) or fib(1) edge cases.

void test_fibonacci() {
    assert(fibonacci(5) == 5);
    assert(fibonacci(10) == 55);
}

// --- gcd tests ---
// GAP: does NOT test gcd when one argument is 0.

void test_gcd() {
    assert(gcd(12, 8) == 4);
    assert(gcd(17, 13) == 1);
    assert(gcd(100, 25) == 25);
}

// --- is_prime tests ---
// GAP: does NOT test boundary values (0, 1, 2, negative numbers).

void test_is_prime() {
    assert(is_prime(7) == true);
    assert(is_prime(13) == true);
    assert(is_prime(9) == false);
    assert(is_prime(15) == false);
}

// GAP: clamp is NOT tested at all.
// GAP: factorial is NOT tested at all.

int main() {
    test_add();
    test_subtract();
    test_multiply();
    test_divide();
    test_fibonacci();
    test_gcd();
    test_is_prime();

    std::cout << "All tests passed!" << std::endl;
    return 0;
}
