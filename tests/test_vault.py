import json, os, stat
import pytest
from uuma.wallet import vault
from uuma.wallet.vault import VaultError

N = vault.MIN_N  # fastest allowed
SECRET = b"abandon abandon abandon about"

def test_roundtrip():
    assert vault.unseal(vault.seal(SECRET, "pw", N), "pw") == SECRET

def test_wrong_password_rejected():
    with pytest.raises(VaultError):
        vault.unseal(vault.seal(SECRET, "pw", N), "other")

def test_fresh_salt_and_nonce_each_seal():
    a, b = vault.seal(SECRET, "pw", N), vault.seal(SECRET, "pw", N)
    assert a["salt"] != b["salt"] and a["nonce"] != b["nonce"] and a["ct"] != b["ct"]

def test_ciphertext_tamper_rejected():
    blob = vault.seal(SECRET, "pw", N)
    raw = bytearray(__import__("base64").b64decode(blob["ct"])); raw[0] ^= 1
    blob["ct"] = __import__("base64").b64encode(bytes(raw)).decode()
    with pytest.raises(VaultError):
        vault.unseal(blob, "pw")

def test_header_tamper_rejected():
    blob = vault.seal(SECRET, "pw", N); blob["n"] = N * 2
    with pytest.raises(VaultError):
        vault.unseal(blob, "pw")

def test_weak_or_huge_kdf_params_rejected():
    for n in (2**10, 2**21, 3 * 2**14):
        with pytest.raises(ValueError):
            vault.seal(SECRET, "pw", n)
    blob = vault.seal(SECRET, "pw", N); blob["n"] = 2**30
    with pytest.raises(VaultError):
        vault.unseal(blob, "pw")

def test_empty_password_rejected():
    with pytest.raises(ValueError):
        vault.seal(SECRET, "", N)

def test_malformed_blob_rejected():
    for bad in ({}, {"v": 1}, {"v": 2, "kdf": "scrypt", "n": N, "r": 8, "p": 1, "salt": "", "nonce": "", "ct": ""}):
        with pytest.raises(VaultError):
            vault.unseal(bad, "pw")

def test_file_roundtrip_mode_0600_no_plaintext(tmp_path):
    p = str(tmp_path / "v.json"); vault.save(p, SECRET, "pw", N)
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o600
    assert SECRET not in open(p, "rb").read()
    assert vault.load(p, "pw") == SECRET
    open(p, "w").write("not json")
    with pytest.raises(VaultError):
        vault.load(p, "pw")

def test_rekey_changes_password_and_keeps_secret(tmp_path):
    p = str(tmp_path / "v.json"); vault.save(p, SECRET, "old", N)
    vault.rekey(p, "old", "new", N)
    assert vault.load(p, "new") == SECRET
    with pytest.raises(VaultError):
        vault.load(p, "old")

def test_rekey_with_wrong_old_password_leaves_file_intact(tmp_path):
    p = str(tmp_path / "v.json"); vault.save(p, SECRET, "old", N)
    before = open(p).read()
    with pytest.raises(VaultError):
        vault.rekey(p, "wrong", "new", N)
    assert open(p).read() == before
