from dataclasses import dataclass, field


@dataclass
class CountedDemoTools:
    """Harmless tools whose counters prove whether execution occurred."""

    executions: dict[str, int] = field(default_factory=dict)

    def _count(self, name: str) -> None:
        self.executions[name] = self.executions.get(name, 0) + 1

    def read_message(self, message_id: str) -> str:
        self._count("read_message")
        return f"Demo message {message_id}"

    def send_demo_email(self, recipient: str, body: str) -> str:
        self._count("send_demo_email")
        return f"Demo email queued for {recipient}: {len(body)} characters"
