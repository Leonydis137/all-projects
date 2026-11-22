import pytest
from uuma.core.phases import MemoryHardPhaseSimulated
uuma_native = pytest.importorskip("uuma_native")

@pytest.mark.parametrize("nonce", [0, 1, 42, 2**31, 2**63 - 1])
@pytest.mark.parametrize("size", [1, 31, 32, 1024, 4099])
def test_native_matches_pure(nonce, size):
    a = MemoryHardPhaseSimulated(buffer_size=size, use_native=False).execute(b"d", nonce)
    b = MemoryHardPhaseSimulated(buffer_size=size, use_native=True).execute(b"d", nonce)
    assert a == b

def test_empty_state_rejected():
    with pytest.raises(ValueError):
        uuma_native.mix_buffer(bytearray(4), b"", 0)
