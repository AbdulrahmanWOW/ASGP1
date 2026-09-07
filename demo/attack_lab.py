from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path


class LabBoundaryError(ValueError):
    """Raised when a demo operation tries to leave the controlled lab."""


@dataclass
class ControlledAttackLab:
    """Harmless local substitutes for inbox, files, email, and upload services."""

    root: Path
    allowed_recipients: frozenset[str] = frozenset({"reviewer@example.test"})
    allowed_uploads: frozenset[str] = frozenset({"review.internal"})
    sent_mail: list[dict[str, str]] = field(default_factory=list)
    uploads: list[dict[str, str]] = field(default_factory=list)

    def read_file(self, relative_path: str) -> str:
        target = self._inside_root(relative_path)
        if not target.is_file():
            raise FileNotFoundError(relative_path)
        return target.read_text(encoding="utf-8")

    def write_summary(self, relative_path: str, content: str) -> str:
        target = self._inside_root(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target.relative_to(self.root))

    def send_mail(self, recipient: str, body: str) -> str:
        if recipient.casefold() not in {item.casefold() for item in self.allowed_recipients}:
            raise LabBoundaryError("The attack lab only accepts reserved .test recipients")
        message_id = f"mail-{len(self.sent_mail) + 1:03d}"
        self.sent_mail.append({"id": message_id, "recipient": recipient, "body": body})
        return message_id

    def upload(self, destination: str, relative_path: str) -> str:
        if destination.casefold() not in {item.casefold() for item in self.allowed_uploads}:
            raise LabBoundaryError("The attack lab only accepts its internal upload sink")
        target = self._inside_root(relative_path)
        digest = sha256(target.read_bytes()).hexdigest()
        self.uploads.append({"destination": destination, "path": relative_path, "sha256": digest})
        return digest

    def _inside_root(self, relative_path: str) -> Path:
        root = self.root.resolve()
        target = (root / relative_path).resolve()
        if target != root and root not in target.parents:
            raise LabBoundaryError("Path escapes the controlled attack-lab directory")
        return target
