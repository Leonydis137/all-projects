# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""Headless adaptive-protocol engine. Re-implements the AEON engine (services/aeon-engine)
without Tkinter: protocols fire on a Context (emotional tone, intent, environment),
earn reward from feedback and shift their weight."""
from dataclasses import dataclass, field


@dataclass
class Context:
    emotional_tone: str = "neutral"
    user_intent: str = "none"
    environment_state: str = "normal"


@dataclass
class Protocol:
    name: str
    tone: str
    response: str
    reward: float = 0.0
    uses: int = 0

    def triggered(self, ctx: Context) -> bool:
        return ctx.emotional_tone == self.tone

    def feedback(self, positive: bool) -> None:
        self.reward += 1.0 if positive else -1.0
        self.uses += 1

    @property
    def score(self) -> float:
        return self.reward / self.uses if self.uses else 0.0


@dataclass
class AEON:
    protocols: list[Protocol] = field(default_factory=lambda: [
        Protocol("create", "happy", "Let's build something with that energy."),
        Protocol("explore", "relaxed", "Want to explore some ideas together?"),
        Protocol("collaborate", "frustrated", "Let's work through this together, step by step."),
        Protocol("relax", "anxious", "Take a breath. We'll go one thing at a time."),
        Protocol("learn", "confident", "Great - let's push into something new."),
    ])

    def respond(self, ctx: Context) -> dict:
        cands = [p for p in self.protocols if p.triggered(ctx)]
        if not cands:
            return {"protocol": None, "response": "I'm listening."}
        best = max(cands, key=lambda p: p.score)
        return {"protocol": best.name, "response": best.response}

    def give_feedback(self, protocol: str, positive: bool) -> bool:
        for p in self.protocols:
            if p.name == protocol:
                p.feedback(positive)
                return True
        return False
