from __future__ import annotations
import hashlib

_B58 = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58encode(raw: bytes) -> str:
    n = int.from_bytes(raw, "big")
    out = bytearray()
    while n > 0:
        n, r = divmod(n, 58)
        out.append(_B58[r])
    for byte in raw:
        if byte == 0:
            out.append(_B58[0])
        else:
            break
    return bytes(reversed(out)).decode("ascii")


def base58check_encode(payload: bytes) -> str:
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return _b58encode(payload + checksum)


def p2pkh_address(pubkey_bytes: bytes, mainnet: bool = True) -> str:
    sha = hashlib.sha256(pubkey_bytes).digest()
    h160 = hashlib.new("ripemd160", sha).digest()
    version = b"\x00" if mainnet else b"\x6f"
    return base58check_encode(version + h160)


# ---- Bech32 (BIP173) --------------------------------------------------

_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_BECH32_GEN = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)


def _bech32_polymod(values: list[int]) -> int:
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            chk ^= _BECH32_GEN[i] if ((b >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp: str) -> list[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _bech32_create_checksum(hrp: str, data: list[int]) -> list[int]:
    values = _bech32_hrp_expand(hrp) + data
    polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def _convertbits(data: list[int], frombits: int, tobits: int, pad: bool = True) -> list[int]:
    acc = 0
    bits = 0
    ret: list[int] = []
    maxv = (1 << tobits) - 1
    for value in data:
        acc = (acc << frombits) | value
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad and bits:
        ret.append((acc << (tobits - bits)) & maxv)
    return ret


def bech32_encode(hrp: str, data: list[int]) -> str:
    combined = data + _bech32_create_checksum(hrp, data)
    return hrp + "1" + "".join(_BECH32_CHARSET[d] for d in combined)


def p2wpkh_address(pubkey_compressed: bytes, mainnet: bool = True) -> str:
    if len(pubkey_compressed) != 33:
        raise ValueError("compressed pubkey must be 33 bytes")
    sha = hashlib.sha256(pubkey_compressed).digest()
    h160 = hashlib.new("ripemd160", sha).digest()
    data = [0] + _convertbits(list(h160), 8, 5, True)
    return bech32_encode("bc" if mainnet else "tb", data)


# ---- Ethereum (Keccak-256 + EIP-55) ----------------------------------

def ethereum_address(pubkey_uncompressed_64: bytes) -> str:
    """64-byte raw pubkey (x||y), no 0x04 prefix. EIP-55 checksummed."""
    if len(pubkey_uncompressed_64) != 64:
        raise ValueError("need 64 bytes (no 0x04 prefix)")

    try:
        from Crypto.Hash import keccak
    except ImportError as e:
        raise RuntimeError(
            "pycryptodome required for Keccak-256 "
            "(hashlib.sha3_256 is NOT Keccak)"
        ) from e

    k = keccak.new(digest_bits=256)
    k.update(pubkey_uncompressed_64)
    addr = k.digest()[-20:]
    hex_addr = addr.hex()

    k2 = keccak.new(digest_bits=256)
    k2.update(hex_addr.encode("ascii"))
    checksum = k2.hexdigest()

    out = "0x" + "".join(
        c.upper() if int(checksum[i], 16) >= 8 else c
        for i, c in enumerate(hex_addr)
    )
    return out
