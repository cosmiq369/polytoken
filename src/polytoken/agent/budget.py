"""Thread-safe physical-attempt and monotonic deadline limits."""
import threading
import time
from ..llm import LLMError


class BudgetExceeded(LLMError):
    pass


class BudgetGuard:
    LIMITS = {'nemotron': 25, 'judge': 45, 'hosted': 70, 'sql': 60}

    def __init__(self, *, clock=time.monotonic, wall_s=360, cancel_event=None):
        self.cancel_event = cancel_event
        self.clock, self.wall_s = clock, wall_s
        # Stop external work early enough to check and serialize a partial report.
        self.finalize_reserve_s = min(2., wall_s / 10)
        self.started = clock()
        self.counts = dict.fromkeys(self.LIMITS, 0)
        self.reason = None
        self.lock = threading.Lock()

    def remaining(self):
        return max(0., self.wall_s - self.finalize_reserve_s - (self.clock() - self.started))

    def check(self):
        if self.cancel_event is not None and self.cancel_event.is_set():
            self.reason = "Stopped by user"
        if self.remaining() <= 0:
            self.reason = 'wall time budget spent'
        if self.reason:
            raise BudgetExceeded(self.reason)

    def consume(self, kind):
        with self.lock:
            self.check()
            if self.counts[kind] >= self.LIMITS[kind]:
                self.reason = kind + ' call budget spent'
                raise BudgetExceeded(self.reason)
            self.counts[kind] += 1

    def snapshot(self):
        return {**self.counts, 'duration_s': self.clock() - self.started,
                'remaining_s': self.remaining(), 'reason': self.reason,
                'ceilings': {**self.LIMITS, 'duration_s': self.wall_s}}
