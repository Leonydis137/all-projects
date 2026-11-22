"""Encrypted vault for a wallet secret (e.g. a BIP39 mnemonic).

Author & builder: Juan-louw Greyling <juanlouw.greyling@gmail.com>

Format v1 (JSON): scrypt(password, salt) -> 32-byte key -> AES-256-GCM.
The header (version, kdf, kdf params, salt) is bound as AAD, so editing any
header field makes decryption fail. Research code: no external review.
"""
from __future__ import annotations
import base64, json, os, tempfile
from hashlib import scrypt
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VERSION = 1
DEFAULT_N, R, P = 2**15, 8, 1
MIN_N, MAX_N = 2**14, 2**20  # floor blocks weak files; cap blocks DoS via crafted params


class VaultError(Exception):
    """Wrong password, corrupted/tampered file, or unsupported format."""


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def _key(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return scrypt(password.encode(), salt=salt, n=n, r=r, p=p, maxmem=256 * 1024 * 1024, dklen=32)


def _aad(v: int, n: int, r: int, p: int, salt: str) -> bytes:
    return json.dumps({"v": v, "kdf": "scrypt", "n": n, "r": r, "p": p, "salt": salt}, sort_keys=True).encode()


def seal(secret: bytes, password: str, n: int = DEFAULT_N) -> dict:
    if not password:
        raise ValueError("password must be non-empty")
    if not MIN_N <= n <= MAX_N or n & (n - 1):
        raise ValueError("scrypt n must be a power of two within limits")
    salt, nonce = os.urandom(16), os.urandom(12)
    s = _b64(salt)
    ct = AESGCM(_key(password, salt, n, R, P)).encrypt(nonce, secret, _aad(VERSION, n, R, P, s))
    return {"v": VERSION, "kdf": "scrypt", "n": n, "r": R, "p": P, "salt": s, "nonce": _b64(nonce), "ct": _b64(ct)}


def unseal(blob: dict, password: str) -> bytes:
    try:
        v, n, r, p, s = blob["v"], blob["n"], blob["r"], blob["p"], blob["salt"]
        if v != VERSION or blob["kdf"] != "scrypt":
            raise VaultError("unsupported vault format")
        if not MIN_N <= n <= MAX_N or n & (n - 1) or (r, p) != (R, P):
            raise VaultError("kdf parameters out of range")
        nonce, ct, salt = (base64.b64decode(blob[k], validate=True) for k in ("nonce", "ct", "salt"))
        return AESGCM(_key(password, salt, n, r, p)).decrypt(nonce, ct, _aad(v, n, r, p, s))
    except VaultError:
        raise
    except InvalidTag:
        raise VaultError("wrong password or corrupted vault") from None
    except (KeyError, TypeError, ValueError):
        raise VaultError("malformed vault file") from None


def save(path: str, secret: bytes, password: str, n: int = DEFAULT_N) -> None:
    """Atomic write, file mode 0600."""
    blob = seal(secret, password, n)
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(blob, f)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load(path: str, password: str) -> bytes:
    try:
        with open(path) as f:
            blob = json.load(f)
    except json.JSONDecodeError:
        raise VaultError("malformed vault file") from None
    return unseal(blob, password)


def rekey(path: str, old_password: str, new_password: str, n: int = DEFAULT_N) -> None:
    """Change the password. Decrypts first; the file is untouched if old_password is wrong."""
    save(path, load(path, old_password), new_password, n)
