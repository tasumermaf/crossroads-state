"""Independent coordinate-dictionary oracle for synthetic-ternary-v1.

Does not call the production Engine, Operation, permutation helper, fixture
generator, or wrapping helper. Independence is implementation-level; this is
not external peer review and both implementations share the stated specification.
"""
from fractions import Fraction
from itertools import product

ADDRESSES = tuple(product((-1, 0, 1), repeat=4))


def wrap(x):
    while x > 1:
        x -= 3
    while x < -1:
        x += 3
    return x


def move(p, delta, count):
    return tuple(wrap(p[j] + count * delta[j]) for j in range(4))


class Oracle:
    def __init__(self, plain):
        self.field = {p: Fraction(v) for p, v in zip(ADDRESSES, plain["values"])}
        self.reader = tuple(ADDRESSES[i] for i in plain["reader"])
        self.reference = ADDRESSES[plain["reference"]]

    def plain(self):
        return {"values": [str(self.field[p]) for p in ADDRESSES],
                "reader": [ADDRESSES.index(p) for p in self.reader],
                "reference": ADDRESSES.index(self.reference)}

    def step(self, name, count):
        if name in ("A", "B", "M"):
            for p in ADDRESSES:
                delta = (wrap(sum(p)) if name == "A" else
                         wrap(p[0] - p[1] + p[2] - p[3]) if name == "B" else -1)
                self.field[p] += count * delta
            if name == "B":
                self.reader = tuple(move(p, (0, 1, 1, 0), count) for p in self.reader)
        elif name == "S":
            self.reader = tuple(move(p, (-1, -1, 1, 1), count) for p in self.reader)
        elif name in ("R", "U"):
            for _ in range(count % 3):
                mapping = (lambda p: (p[2], p[1], p[3], p[0])) if name == "R" else (
                    lambda p: move(p, (0, 1, 1, 0), 1))
                self.field = {mapping(p): value for p, value in self.field.items()}
                self.reader = tuple(mapping(p) for p in self.reader)
                self.reference = mapping(self.reference)
        else:
            raise ValueError("Unknown operation")
        return self
