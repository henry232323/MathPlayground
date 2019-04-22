from random import randint

question = "Find the zeroes of the equation"

def quadratic(**kwargs):
    if "z1" in kwargs:
        z1 = int(kwargs['z1'])
    else:
        z1 = randint(-10, 10)

    if "z2" in kwargs:
        z2 = int(kwargs['z2'])
    else:
        z2 = randint(-10, 10)

    if "k" in kwargs:
        k = kwargs['k']
    else:
        k = randint(-5, 5)
        if k == 0:
            k = 1

    a, b, c = k, k * (-z1 + -z2), k * (-z1) * (-z2)
    if abs(a) == 1:
        apart = f"{'-' if a < 0 else ''}x^2"
    elif a != 0:
        apart = f"{a}x^2"
    else:
        apart = ""

    if abs(b) == 1:
        bpart = f"{'-' if b < 0 else '+'} x"
    elif b != 0:
        bpart = f"{'-' if b < 0 else '+'} {abs(b)}x"
    else:
        bpart = ""

    if c != 0:
        cpart = f"{'-' if c < 0 else '+'} {abs(c)}"
    else:
        cpart = ""

    return ["{}{}{}".format(apart, bpart, cpart).strip()], [a, b, c, k], {z1, z2}, question