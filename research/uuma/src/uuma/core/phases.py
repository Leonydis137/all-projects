from __future__ import annotations
import hashlib


class ComputationalPhase:
    name = "computational"

    def execute(self, data: bytes, nonce: int) -> bytes:
        x = hashlib.sha256(data + nonce.to_bytes(8, "big")).digest()
        x = hashlib.sha3_256(x).digest()
        x = hashlib.blake2b(x, digest_size=32).digest()
        return x


try:
    import uuma_native as _native
except ImportError:  # optional C hot path
    _native = None


class MemoryHardPhaseSimulated:
    """Scrypt-stress phase. NOT Scrypt, NOT Litecoin's PoW."""
    name = "memory_hard_simulated"

    def __init__(self, rounds: int = 8, buffer_size: int = 1024, use_native: bool = True) -> None:
        self.use_native = use_native and _native is not None
        self.rounds = rounds
        self.buffer_size = buffer_size

    def execute(self, data: bytes, nonce: int) -> bytes:
        buf = bytearray(self.buffer_size)
        state = hashlib.sha256(data + nonce.to_bytes(8, "big")).digest()
        for i in range(self.rounds):
            if self.use_native:
                _native.mix_buffer(buf, state, i)
            else:
                for j in range(self.buffer_size):
                    buf[j] = (state[j % len(state)] + i + j) & 0xFF
            state = hashlib.sha256(buf).digest()
            if i % 2 == 0:
                state = hashlib.scrypt(
                    state, salt=b"uuma_sim_salt", n=1024, r=1, p=1
                )
        return state


class CPUFriendlyPhaseSimulated:
    """Algorithm-switching phase. NOT RandomX."""
    name = "cpu_friendly_simulated"

    def execute(self, data: bytes, nonce: int) -> bytes:
        state = hashlib.sha256(data + nonce.to_bytes(8, "big")).digest()
        algos = (
            lambda b: hashlib.sha256(b).digest(),
            lambda b: hashlib.sha3_256(b).digest(),
            lambda b: hashlib.blake2b(b, digest_size=32).digest(),
            lambda b: hashlib.blake2s(b).digest(),
        )
        for i in range(12):
            state = algos[(state[0] + i) % len(algos)](state)
            if state[1] % 2 == 0:
                state = hashlib.sha3_512(state).digest()[:32]
            else:
                state = hashlib.blake2s(state).digest()
        return state


class MixingPhaseSimulated:
    """Byte-mixing phase. NOT CryptoNight, NOT Equihash."""
    name = "mixing_simulated"

    def execute(self, data: bytes, nonce: int) -> bytes:
        state = hashlib.sha256(data + nonce.to_bytes(8, "big")).digest()
        for r in range(4):
            mixed = bytearray(32)
            for i in range(32):
                mixed[i] = state[(i + r) % len(state)] ^ state[(i * 7) % len(state)]
            state = hashlib.sha3_256(bytes(mixed)).digest()
        cache = [
            hashlib.sha256(state + i.to_bytes(2, "big")).digest() for i in range(64)
        ]
        final = bytearray(32)
        for item in cache:
            for i in range(32):
                final[i] ^= item[i]
        return hashlib.sha3_256(bytes(final)).digest()


class ASICResistancePhaseSimulated:
    """Data-dependent branch phase. NOT ProgPow, NOT KawPow."""
    name = "asic_resistance_simulated"

    def __init__(self, puzzle_variations: int = 1024) -> None:
        self.puzzle_variations = puzzle_variations

    def execute(self, data: bytes, nonce: int) -> bytes:
        seed = nonce % self.puzzle_variations
        state = hashlib.sha256(data + nonce.to_bytes(8, "big")).digest()
        for i in range(6):
            state = self._math(state, seed + i)
            state = hashlib.sha256(state).digest()
            if i % 3 == 0:
                state = self._mem(state, seed)
        return state

    @staticmethod
    def _math(data: bytes, seed: int) -> bytes:
        nums = list(data[:32])
        out = bytearray(32)
        for i in range(32):
            out[i] = (nums[i] * (seed or 1) + nums[(i + seed) % 32] ** 2) & 0xFF
        return bytes(out)

    @staticmethod
    def _mem(data: bytes, seed: int) -> bytes:
        buf = list(data) * 4
        out = bytearray(32)
        L = len(buf)
        for i in range(32):
            idx = (i * (seed or 1) + i * i) % L
            out[i] = buf[idx] ^ buf[(idx + 17) % L]
        return bytes(out)


def build_default_simulated_phases() -> list:
    return [
        ComputationalPhase(),
        MemoryHardPhaseSimulated(),
        CPUFriendlyPhaseSimulated(),
        MixingPhaseSimulated(),
        ASICResistancePhaseSimulated(),
    ]
