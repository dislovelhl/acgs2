import time
from contextlib import contextmanager


class TestContext:
    def __init__(self, chain_state="clean", initial_time=None):
        self.state = chain_state
        self.time_offset = 0
        self.start_time = initial_time or time.time()
        self.governance_phase = "IDLE"

    def set_time_offset(self, seconds):
        self.time_offset = seconds
        print(f"⏰ Time shifted by {seconds}s")

    def current_time(self):
        return self.start_time + self.time_offset

    @contextmanager
    def time_shift(self, seconds):
        old_offset = self.time_offset
        self.set_time_offset(seconds)
        yield
        self.set_time_offset(old_offset)

    def set_phase(self, phase):
        self.governance_phase = phase
        print(f"🏛️ Governance phase changed to: {phase}")


# Example usage in pytest
# @pytest.fixture
# def ctx():
#     return TestContext()
