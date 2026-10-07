"""Rule-based auto tagger driven by rules/tags.yaml."""

import re
from pathlib import Path

import yaml


class Tagger:
    def __init__(self, rules_path: Path) -> None:
        self.rules: dict[str, dict] = {}
        if rules_path.exists():
            data = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
            self.rules = data.get("tags", {}) or {}

    def score(self, text: str) -> dict[str, float]:
        low = text.lower()
        out: dict[str, float] = {}
        for tag, rule in self.rules.items():
            w = float(rule.get("weight", 1.0))
            hits = sum(1 for k in rule.get("keywords", []) if str(k).lower() in low)
            hits += sum(1 for rx in rule.get("regex", []) if re.search(rx, text, re.I))
            out[tag] = hits * w
        return out

    def tag(self, text: str) -> list[str]:
        scores = self.score(text)
        return [t for t, s in scores.items() if s >= float(self.rules[t].get("threshold", 1.0))]
