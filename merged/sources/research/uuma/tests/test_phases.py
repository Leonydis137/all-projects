import pytest
from uuma.core.phases import (
    ComputationalPhase,
    MemoryHardPhaseSimulated,
    CPUFriendlyPhaseSimulated,
    MixingPhaseSimulated,
    ASICResistancePhaseSimulated,
    build_default_simulated_phases,
)

PHASE_FACTORIES = [
    ("computational", lambda: ComputationalPhase()),
    ("memory_hard", lambda: MemoryHardPhaseSimulated(rounds=2, buffer_size=256)),
    ("cpu_friendly", lambda: CPUFriendlyPhaseSimulated()),
    ("mixing", lambda: MixingPhaseSimulated()),
    ("asic_resistance", lambda: ASICResistancePhaseSimulated(puzzle_variations=16)),
]


@pytest.mark.parametrize("name,factory", PHASE_FACTORIES)
@pytest.mark.parametrize("nonce", [0, 1, 42, 2**31])
def test_phase_is_deterministic(name, factory, nonce):
    phase = factory()
    data = b"uuma-test-input"
    a = phase.execute(data, nonce)
    b = phase.execute(data, nonce)
    assert a == b
    assert isinstance(a, bytes)


@pytest.mark.parametrize("name,factory", PHASE_FACTORIES)
def test_phase_output_is_32_bytes(name, factory):
    phase = factory()
    assert len(phase.execute(b"data", 0)) == 32


@pytest.mark.parametrize("name,factory", PHASE_FACTORIES)
def test_phase_output_changes_with_nonce(name, factory):
    phase = factory()
    assert phase.execute(b"data", 0) != phase.execute(b"data", 1)


def test_default_registry_is_five_named_phases():
    names = [p.name for p in build_default_simulated_phases()]
    assert names == [
        "computational",
        "memory_hard_simulated",
        "cpu_friendly_simulated",
        "mixing_simulated",
        "asic_resistance_simulated",
    ]
