while True:
    goal = get_goal()
    plan = plan_actions(goal)

    for action in plan:
        ethics_engine.validate(action)
        execute(action)
