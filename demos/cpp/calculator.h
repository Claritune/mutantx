#ifndef CALCULATOR_H
#define CALCULATOR_H

class Calculator {
public:
    double add(double a, double b);
    double subtract(double a, double b);
    double multiply(double a, double b);
    double divide(double a, double b);
};

// Free functions
double clamp(double value, double min_val, double max_val);

unsigned long long factorial(int n);

unsigned long long fibonacci(int n);

unsigned long long gcd(unsigned long long a, unsigned long long b);

bool is_prime(int n);

#endif // CALCULATOR_H
