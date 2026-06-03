from dataclasses import dataclass
from typing import Any

from app.decision_engine.gemini_client import GeminiClient
from app.models.event import Event
from app.rules.rule_engine import RuleEngine


@dataclass(frozen=True)
class AgentDecision:
    priority: str
    classification: str
    summary: str
    recommendations: list[Any]
    rule_triggered: str | None


class BusinessAgent:
    def __init__(
        self,
        rule_engine: RuleEngine,
        gemini_client: GeminiClient,
    ) -> None:
        self.rule_engine = rule_engine
        self.gemini_client = gemini_client

    def analyze(self, event: Event) -> AgentDecision:
        rule_result = self.rule_engine.evaluate(event)
        gemini_result = self.gemini_client.analyze_event(event)

        return AgentDecision(
            priority=rule_result.priority,
            classification=gemini_result["classification"],
            summary=gemini_result["summary"],
            recommendations=gemini_result["recommendations"],
            rule_triggered=rule_result.rule_triggered,
        )
