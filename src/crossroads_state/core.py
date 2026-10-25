"""Finite exact-state engine. No network, inference, or private data dependencies."""
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import re
from typing import Iterable
from types import MappingProxyType

SCHEMA = "crossroads-state.checkpoint.v1"
RATIONAL = re.compile(r"-?\d+(?:/[1-9]\d*)?\Z")


def canonical(data: object) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(data: object) -> str:
    return hashlib.sha256(canonical(data)).hexdigest()


def _integer(value: object) -> bool:
    return type(value) is int


def _parse_rational(value: object) -> Fraction:
    if not isinstance(value, str) or not RATIONAL.fullmatch(value):
        raise ValueError("Expected an exact rational string, e.g. '4' or '-2/3'")
    return Fraction(value)


@dataclass(frozen=True)
class State:
    """Array + ordered reader + carried reference. The route is not the history."""
    values: tuple[Fraction, ...]
    reader: tuple[int, ...]
    reference: int

    def __post_init__(self) -> None:
        if not isinstance(self.values, tuple) or not self.values:
            raise ValueError("Values must be a nonempty tuple")
        if any(not isinstance(v, Fraction) for v in self.values):
            raise ValueError("Values must be exact Fraction instances")
        n = len(self.values)
        if (not isinstance(self.reader, tuple) or not self.reader
                or any(not _integer(i) or not 0 <= i < n for i in self.reader)
                or len(set(self.reader)) != len(self.reader)):
            raise ValueError("Reader must contain distinct valid integer indices")
        if not _integer(self.reference) or not 0 <= self.reference < n:
            raise ValueError("Reference must be a valid integer index")

    def observe(self) -> tuple[Fraction, ...]:
        return tuple(self.values[i] for i in self.reader)

    def plain(self) -> dict:
        return {"values": [str(v) for v in self.values],
                "reader": list(self.reader), "reference": self.reference}

    @classmethod
    def parse(cls, data: object) -> "State":
        if not isinstance(data, dict) or set(data) != {"values", "reader", "reference"}:
            raise ValueError("Invalid state fields")
        if not isinstance(data["values"], list) or not isinstance(data["reader"], list):
            raise ValueError("Values and reader must be JSON arrays")
        return cls(tuple(_parse_rational(v) for v in data["values"]),
                   tuple(data["reader"]), data["reference"])


@dataclass(frozen=True)
class Operation:
    """An additive field and/or a reader permutation, OR a passive reframe.

    permutation[old_index] is the new index. Reader changes can commute with
    an additive field because they act on different components. Reframing
    and addition cannot be combined here: their naive inverse need not commute.
    """
    delta: tuple[Fraction, ...] | None = None
    permutation: tuple[int, ...] | None = None
    reframe: bool = False

    def validate(self, size: int) -> None:
        if type(self.reframe) is not bool:
            raise ValueError("reframe is boolean")
        if self.delta is not None and (not isinstance(self.delta, tuple) or len(self.delta) != size or
                                      any(not isinstance(x, Fraction) for x in self.delta)):
            raise ValueError("Delta must contain one exact Fraction per address")
        if self.permutation is not None and (
                not isinstance(self.permutation, tuple) or len(self.permutation) != size or
                any(not _integer(i) for i in self.permutation) or
                sorted(self.permutation) != list(range(size))):
            raise ValueError("Invalid address permutation")
        if self.reframe and (self.permutation is None or self.delta is not None):
            raise ValueError("A passive reframe needs a permutation and no delta")
        if self.delta is None and self.permutation is None:
            raise ValueError("Empty operation")

    def plain(self) -> dict:
        return {"delta": None if self.delta is None else [str(x) for x in self.delta],
                "permutation": None if self.permutation is None else list(self.permutation),
                "reframe": self.reframe}


def permutation_power(permutation: tuple[int, ...], count: int) -> tuple[int, ...]:
    """Cycle decomposition works for any finite permutation and signed count."""
    result = list(range(len(permutation)))
    visited = set()
    for start in range(len(permutation)):
        if start in visited:
            continue
        cycle, current = [], start
        while current not in visited:
            visited.add(current)
            cycle.append(current)
            current = permutation[current]
        for j, old in enumerate(cycle):
            result[old] = cycle[(j + count) % len(cycle)]
    return tuple(result)


class Engine:
    def __init__(self, size: int, reader_size: int, operations: dict[str, Operation],
                 name: str = "finite-state-model") -> None:
        if not _integer(size) or not _integer(reader_size) or not 0 < reader_size <= size:
            raise ValueError("Invalid model dimensions")
        if not isinstance(name, str) or not name or not operations:
            raise ValueError("A named model needs operations")
        for key, operation in operations.items():
            if not isinstance(key, str) or not key or not isinstance(operation, Operation):
                raise ValueError("Invalid operation definition")
            operation.validate(size)
        self.size, self.reader_size = size, reader_size
        self.operations = MappingProxyType(dict(operations))
        self.definition = {"name": name, "size": size, "reader_size": reader_size,
                           "operations": {k: v.plain() for k, v in operations.items()}}
        self.model_id = digest(self.definition)

    def validate(self, state: State) -> None:
        if len(state.values) != self.size or len(state.reader) != self.reader_size:
            raise ValueError("State dimensions do not match this model")

    def step(self, state: State, name: str, count: int = 1) -> State:
        self.validate(state)
        if not _integer(count) or name not in self.operations:
            raise ValueError("Instruction needs a known name and an integer count")
        op = self.operations[name]
        values, reader, reference = state.values, state.reader, state.reference
        if op.delta is not None:
            values = tuple(x + count * d for x, d in zip(values, op.delta))
        if op.permutation is not None:
            move = permutation_power(op.permutation, count)
            reader = tuple(move[i] for i in reader)
            if op.reframe:
                new_values = [Fraction(0)] * self.size
                for old, new in enumerate(move):
                    new_values[new] = values[old]
                values = tuple(new_values)
                reference = move[reference]
        return State(values, reader, reference)

    def run(self, state: State, journal: Iterable[tuple[str, int]]) -> State:
        self.validate(state)
        for name, count in journal:
            state = self.step(state, name, count)
        return state


def inverse(journal: Iterable[tuple[str, int]]) -> list[tuple[str, int]]:
    return [(name, -count) for name, count in reversed(list(journal))]


def pack(state: State, engine: Engine) -> dict:
    engine.validate(state)
    payload = {"schema": SCHEMA, "model_id": engine.model_id, "state": state.plain()}
    return {"payload": payload, "sha256": digest(payload)}


def unpack(document: object, engine: Engine) -> State:
    if not isinstance(document, dict) or set(document) != {"payload", "sha256"}:
        raise ValueError("Invalid checkpoint fields")
    payload = document["payload"]
    if not isinstance(payload, dict) or set(payload) != {"schema", "model_id", "state"}:
        raise ValueError("Invalid checkpoint payload")
    if digest(payload) != document["sha256"]:
        raise ValueError("Checksum mismatch")
    if payload["schema"] != SCHEMA or payload["model_id"] != engine.model_id:
        raise ValueError("Checkpoint belongs to a different schema or model")
    state = State.parse(payload["state"])
    engine.validate(state)
    return state


def parse_journal(data: object) -> list[tuple[str, int]]:
    if not isinstance(data, list):
        raise ValueError("Journal must be a JSON array")
    result = []
    for item in data:
        if (not isinstance(item, list) or len(item) != 2 or
                not isinstance(item[0], str) or not _integer(item[1])):
            raise ValueError("Each instruction is [name, integer count]")
        result.append((item[0], item[1]))
    return result
