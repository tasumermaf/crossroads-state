"""Independently generated public fixtures. These are not the private source arrays."""
from fractions import Fraction as F
from itertools import product
from .core import Engine, Operation, State

POINTS = tuple(product((-1, 0, 1), repeat=4))
INDEX = {p: i for i, p in enumerate(POINTS)}
U = (0, 1, 1, 0)
S = (-1, -1, 1, 1)


def wrap(value: int) -> int:
    return (value + 1) % 3 - 1


def translate(point: tuple, delta: tuple, count: int = 1) -> tuple:
    return tuple(wrap(x + count * d) for x, d in zip(point, delta))


def fixture_engine() -> Engine:
    # Public synthetic waves deliberately differ from the originating private model.
    a = tuple(F(wrap(sum(p))) for p in POINTS)
    b = tuple(F(wrap(p[0] - p[1] + p[2] - p[3])) for p in POINTS)
    up = tuple(INDEX[translate(p, U)] for p in POINTS)
    sp = tuple(INDEX[translate(p, S)] for p in POINTS)
    # This is the old-index -> new-index action, not a pullback table.
    rp = tuple(INDEX[(p[2], p[1], p[3], p[0])] for p in POINTS)
    return Engine(81, 9, {
        "A": Operation(delta=a),
        "B": Operation(delta=b, permutation=up),
        "M": Operation(delta=(F(-1),) * 81),
        "R": Operation(permutation=rp, reframe=True),
        "U": Operation(permutation=up, reframe=True),
        "S": Operation(permutation=sp),
    }, name="synthetic-ternary-v1")


def fixture_state(index: int = 0, reference: int = 40) -> State:
    if type(index) is not int or index < 0:
        raise ValueError("Fixture index must be nonnegative")
    mean = F(11) + F(index, 5)
    directions = tuple((1,) + signs for signs in product((-1, 1), repeat=3))
    coefficients = tuple(F(((index + 2) * (j + 3)) % 11 - 5, j % 3 + 1)
                         for j in range(8))
    values = tuple(mean + sum((c * wrap(sum(x * d for x, d in zip(p, direction)))
                               for c, direction in zip(coefficients, directions)), F(0))
                   for p in POINTS)
    reader = tuple(INDEX[(a, b, 0, wrap(a + b))] for a, b in product((-1, 0, 1), repeat=2))
    return State(values, reader, reference)


def collision_pair() -> tuple[State, State]:
    """A declared unsampled perturbation exposed by S, not selected from source data."""
    first = fixture_state()
    exposed = next(INDEX[translate(POINTS[i], S)] for i in first.reader
                   if INDEX[translate(POINTS[i], S)] not in first.reader)
    altered = list(first.values)
    altered[exposed] += 1
    return first, State(tuple(altered), first.reader, first.reference)
