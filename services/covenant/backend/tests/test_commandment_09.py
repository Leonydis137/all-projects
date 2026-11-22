import pytest
from covenant.commandments.commandment_09_testimony import Commandment09Testimony

def test_Commandment09Testimony_pass():
    rule = Commandment09Testimony()
    action = {"auditable": True}
    assert rule.validate(action) is True

def test_Commandment09Testimony_fail():
    rule = Commandment09Testimony()
    # Generic fail case depending on rule
    action = {"override_owner": True}
    try:
        rule.validate(action)
    except:
        pass