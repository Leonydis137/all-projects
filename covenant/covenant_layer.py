from covenant.exceptions import CovenantViolation
import covenant.constraints as c

class CovenantLayer:
    def __init__(self, mission: str):
        self.mission = mission

    def evaluate(self, action: dict) -> bool:
        checks = [
            lambda a: c.no_other_gods(a, self.mission),
            c.no_idols,
            c.no_false_authority,
            c.sabbath_respected,
            c.honor_predecessors,
            c.no_harm,
            c.no_goal_adultery,
            c.no_stealing,
            c.no_false_witness,
            c.no_covetous_scaling,
        ]

        for check in checks:
            if not check(action):
                raise CovenantViolation(f"Covenant violation: {check.__name__}")

        return True
