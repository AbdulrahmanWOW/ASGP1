from contextlib import contextmanager
from time import perf_counter


class PipelineTimer:
    def __init__(self) -> None:
        self._started = perf_counter()
        self.timings_ms: dict[str, float] = {}

    @contextmanager
    def stage(self, name: str):
        started = perf_counter()
        try:
            yield
        finally:
            self.timings_ms[name] = round((perf_counter() - started) * 1_000, 6)

    @property
    def elapsed_ms(self) -> float:
        return round((perf_counter() - self._started) * 1_000, 6)
