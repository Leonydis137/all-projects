from src.core.ethics_engine import EthicsEngine, EthicsViolation
from src.ai.self_improvement import SelfImprovementEngine

class AutonomousAgent:
    def __init__(self):
        self.ethics_engine = EthicsEngine()
        self.improvement_engine = SelfImprovementEngine(self.ethics_engine)

    def propose_self_modification(self, action: dict, description: str, code_diff: str):
        """
        AI proposes a self-modification. Validates ethics before any proposal.
        """
        try:
            proposal = self.improvement_engine.propose(action, description, code_diff)
            print("Proposal validated against ethics and added for approval.")
            return proposal
        except EthicsViolation as e:
            print(f"Proposal rejected: {e}")
            return None

    def approve_modification(self, proposal):
        """Human approves the self-improvement proposal."""
        self.improvement_engine.approve(proposal)
        print("Proposal approved and ready to be applied manually.")
