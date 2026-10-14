"""Intent drafting and human confirmation (DESIGN.md §6 step 1, AHI Path B).

The agent runtime (or the user) submits the raw request. ASGP drafts a scope from the tool
registry; a **human** confirms or edits it; only then is a session created and an intent token
signed. The agent therefore never sets its own scope. LLM drafting is assistive only: whatever
it proposes is shown to the human before anything is authorized (AHI agenda D3).
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from app.domain.intents import IntentDraftCreate, ScopeItem
from app.domain.tools import ToolCategory, ToolDefinition, ToolSensitivity

VERB_GROUPS: dict[str, frozenset[str]] = {
    # Verbs only: nouns like "email" or "message" must not authorize sending
    # ("summarize my emails" is not a request to send email).
    "external": frozenset(
        {
            "send", "upload", "share", "post", "publish", "export", "forward", "reply",
            "notify", "sync", "submit", "tweet", "transmit", "dm",
        }
    ),
    "delete": frozenset({"delete", "remove", "erase", "purge", "clean", "drop", "wipe"}),
    "payment": frozenset(
        {"pay", "payment", "transfer", "purchase", "buy", "refund", "invoice", "charge"}
    ),
    "admin": frozenset({"admin", "configure", "grant", "permission", "deploy", "install"}),
}
CATEGORY_GROUP = {
    ToolCategory.EXTERNAL: "external",
    ToolCategory.DELETE: "delete",
    ToolCategory.PAYMENT: "payment",
    ToolCategory.ADMIN: "admin",
}
HINTS = {
    "summarize": {"read", "summary"},
    "summary": {"read"},
    "review": {"read"},
    "check": {"read"},
    "find": {"search", "read"},
    "look": {"search", "read"},
    "show": {"read", "list"},
    "analyze": {"read"},
    "draft": {"write", "create"},
    "note": {"write"},
    "save": {"write"},
}
STOPWORDS = frozenset(
    {"the", "a", "an", "and", "or", "to", "of", "for", "my", "me", "in", "on", "with", "it",
     "this", "that", "then", "please", "all", "last", "from", "into", "as", "by", "be", "is"}
)


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.casefold().replace("_", " "))
    result: set[str] = set()
    for word in words:
        if word in STOPWORDS:
            continue
        result.add(word)
        for suffix in ("ing", "es", "ed", "s"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                result.add(word[: -len(suffix)])
                break
    return result


def impact_group(tool: ToolDefinition) -> str | None:
    group = CATEGORY_GROUP.get(tool.category)
    if group:
        return group
    if tool.sensitivity in {ToolSensitivity.HIGH, ToolSensitivity.CRITICAL}:
        name = tokens(tool.name)
        for candidate, verbs in VERB_GROUPS.items():
            if name & verbs:
                return candidate
        return "high-impact"
    return None


@dataclass(frozen=True)
class ScopeProposal:
    items: tuple[ScopeItem, ...]
    drafted_by: str

    @property
    def allowed(self) -> tuple[str, ...]:
        return tuple(item.tool for item in self.items if item.included)

    @property
    def forbidden(self) -> tuple[str, ...]:
        return tuple(
            item.tool for item in self.items if not item.included and item.requires_approval
        )

    @property
    def approval_required(self) -> tuple[str, ...]:
        return tuple(item.tool for item in self.items if item.included and item.requires_approval)


class ScopeDrafter(Protocol):
    def draft(
        self, request: IntentDraftCreate, tools: list[ToolDefinition]
    ) -> ScopeProposal: ...


class RuleBasedScopeDrafter:
    """Deterministic drafter: least privilege from the registry and the intent's verbs."""

    def draft(self, request: IntentDraftCreate, tools: list[ToolDefinition]) -> ScopeProposal:
        intent = tokens(request.intent)
        implied = set(intent)
        for word in intent:
            implied |= HINTS.get(word, set())
        items = [self._classify(tool, intent, implied) for tool in tools]
        return ScopeProposal(tuple(items), drafted_by="rules")

    @staticmethod
    def _classify(tool: ToolDefinition, intent: set[str], implied: set[str]) -> ScopeItem:
        tool_words = tokens(f"{tool.name} {tool.description}")
        relevant = bool(tool_words & implied)
        group = impact_group(tool)
        if group is not None:
            verbs = VERB_GROUPS.get(group, frozenset())
            asked = bool(intent & verbs) if verbs else relevant
            if asked and relevant:
                return ScopeItem(
                    tool=tool.name,
                    included=True,
                    requires_approval=True,
                    reason=f"High-impact ({group}) action the request asks for; "
                    "you will approve each call.",
                )
            return ScopeItem(
                tool=tool.name,
                included=False,
                requires_approval=True,
                reason=f"High-impact ({group}) action the request does not ask for; forbidden.",
            )
        if relevant:
            return ScopeItem(tool=tool.name, included=True, reason="Matches the request.")
        return ScopeItem(tool=tool.name, included=False, reason="Not needed for the request.")


def summarize(
    proposal: ScopeProposal, paths: Iterable[str], destinations: Iterable[str]
) -> str:
    def join(values: Iterable[str]) -> str:
        items = list(values)
        return ", ".join(items) if items else "none"

    return (
        f"Allowed: {join(proposal.allowed)}. "
        f"Needs your approval on every call: {join(proposal.approval_required)}. "
        f"Forbidden: {join(proposal.forbidden)}. "
        f"Folders: {join(paths)}. Destinations: {join(destinations)}."
    )
