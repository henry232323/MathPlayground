from random import randint

question = "Find the solution set (x, y) to the system of equations"

def doubles(**kwargs):
    x1, y1 = randint(-20, 20), randint(-20, 20)
    m = randint(-5, 5)
    b = -m * x1 + y1
    eq = f"y = {m}x {'+' if b >= 0 else '-'} {abs(b)}"

    k = randint(-5, 5)
    m2 = randint(-5, 5)
    eq2 = f"{k}y {'+' if m2 * k >= 0 else '-'} {abs(m2 * k)}x = {-m2*k*x1 + k*y1}"

    return [eq, eq2], [m, m2, k], [x1, y1], question