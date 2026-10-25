"""Causal console spans. Telemetry is never treated as a checked business claim."""
from contextlib import contextmanager
from contextvars import ContextVar
import re
import time
from uuid import uuid4

_PARENT = ContextVar('polytoken_span', default=None)


def safe_explanation(text):
    """Fail closed on numeric planner prose, including Indic digits and word numbers.

    Planner prose is not evidence. Retain qualitative explanations only; quantities
    belong in checker-approved claim cards with receipts.
    """
    text = str(text)
    if any(c.isnumeric() for c in text) or re.search(r'\d|[%₹$€£]|\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|twice|thrice|quarter|hundred|thousand|million|billion|half|double|triple|percent)\b', text, re.I):
        return 'The planner selected this step using the available evidence. Quantities are shown only in checked findings.'
    return text


class Trace:
    def __init__(self, emit):
        self.emit = emit
        self.tool_parent = None

    @contextmanager
    def span(self, kind, *, service, name, parent_id=None, **fields):
        identifier = uuid4().hex
        parent = parent_id or _PARENT.get() or self.tool_parent
        start = time.monotonic()
        row = dict(span_id=identifier, parent_id=parent, service=service, name=name, **fields)
        self.emit(kind + '_started', **row)
        token = _PARENT.set(identifier)
        outcome = {'status': 'ok'}
        try:
            yield outcome
        except Exception as exc:
            outcome.update(status='error', error_class=type(exc).__name__, next_action='Return to the bounded caller for retry or a partial report.')
            raise
        finally:
            _PARENT.reset(token)
            self.emit(kind + '_finished', **row, **outcome, duration_ms=round((time.monotonic()-start)*1000, 3))
