from dataclasses import dataclass

from app.models.event import Event


@dataclass(frozen=True)
class RuleResult:
    priority: str
    classification: str
    rule_triggered: str


class RuleEngine:
    HIGH_PRIORITY_RULE = "payment_failed"
    LOW_PRIORITY_RULE = "payment_succeeded"
    DEFAULT_RULE = "unknown"

    def evaluate(self, event: Event) -> RuleResult:
        event_type = event.event_type.lower()

        if self._matches_failed(event_type):
            return RuleResult(
                priority="high",
                classification=self.HIGH_PRIORITY_RULE,
                rule_triggered=self.HIGH_PRIORITY_RULE,
            )

        if self._matches_succeeded(event_type):
            return RuleResult(
                priority="low",
                classification=self.LOW_PRIORITY_RULE,
                rule_triggered=self.LOW_PRIORITY_RULE,
            )

        return RuleResult(
            priority="medium",
            classification=self.DEFAULT_RULE,
            rule_triggered=self.DEFAULT_RULE,
        )

    def _matches_failed(self, event_type: str) -> bool:
        return event_type == self.HIGH_PRIORITY_RULE or "failed" in event_type

    def _matches_succeeded(self, event_type: str) -> bool:
        return event_type == self.LOW_PRIORITY_RULE or "succeeded" in event_type
