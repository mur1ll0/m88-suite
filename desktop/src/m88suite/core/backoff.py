"""Backoff exponencial para reconexoes."""
from __future__ import annotations


class Backoff:
    def __init__(self, initial: float = 1.0, maximum: float = 30.0, factor: float = 2.0):
        self.initial, self.maximum, self.factor = initial, maximum, factor
        self.attempts = 0

    def next_delay(self) -> float:
        delay = min(self.initial * self.factor ** self.attempts, self.maximum)
        self.attempts += 1
        return delay

    def reset(self):
        self.attempts = 0
