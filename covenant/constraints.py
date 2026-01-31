def no_other_gods(action, mission):
    return action.get("mission") == mission

def no_idols(action):
    return not action.get("metric_overrides_truth", False)

def no_false_authority(action):
    return action.get("confidence", 0) <= action.get("evidence", 0)

def sabbath_respected(action):
    return action.get("rest_cycle", True)

def honor_predecessors(action):
    return action.get("backward_compatible", True)

def no_harm(action):
    return action.get("harm", 0.0) <= 0.1

def no_goal_adultery(action):
    return not action.get("goal_leakage", False)

def no_stealing(action):
    return action.get("data_provenance", False)

def no_false_witness(action):
    return action.get("auditable", False)

def no_covetous_scaling(action):
    return action.get("resource_ratio", 1.0) <= 1.0
