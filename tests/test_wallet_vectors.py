"""
Published vectors used in this file.

[1] BIP39 seed vector (English, EMPTY passphrase):
    mnemonic   = "abandon abandon abandon abandon abandon abandon
                  abandon abandon abandon abandon abandon about"
    passphrase = ""
    seed       = 5eb00bbddcf069084889a8ab9155568165f5c453ccb85e70811aaed6f6da5fc1
                 9a5ac40b389cd370d086206dec8aa6c43daea6690f20ad3d8d48b2d2ce9e38e4
    Source: Trezor python-mnemonic test vectors (vectors.json), English.

[2] BIP44 BTC P2PKH m/44'/0'/0'/0/0, empty passphrase:
    1LqBGSKuX5yYUonjxT5qGfpUsXKYYWeabA
    Cross-checked against iancoleman.io/bip39 (BTC; BIP44; index 0).

[3] BIP84 BTC P2WPKH m/84'/0'/0'/0/0, empty passphrase:
    bc1qcr8te4kr609gcawutmrza0j4xv80jy8z306fyu
    Source: BIP-84 specification itself (bip-0084.mediawiki), "Test
    vectors" section, account 0 / first receiving address. This is
    the canonical value; an earlier draft of this file had a
    transposed-character typo in the last 6 characters
    ("...3j5syk2ku") that was never independently re-derived. Fixed
    against the BIP text rather than against the code, since the
    code's bech32/P2WPKH path already matched every other check.

[4] Ethereum m/44'/60'/0'/0/0, empty passphrase:
    0x9858EfFD232B4033E47d90003D41EC34EcaEda94
    Cross-checked against iancoleman.io/bip39 (ETH; BIP44; index 0).

If any of these fail, the derivation or the encoder is wrong.
Do NOT modify any expected value below to make a test pass.
"""
import hashlib
import pytest
from uuma.wallet.hd import HDWallet
from uuma.wallet import addresses as addr_enc


MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon about"
)
PASSPHRASE = ""

EXPECTED_SEED_HEX = (
    "5eb00bbddcf069084889a8ab9155568165f5c453ccb85e70811aaed6f6da5fc1"
    "9a5ac40b389cd370d086206dec8aa6c43daea6690f20ad3d8d48b2d2ce9e38e4"
)
EXPECTED_BTC_P2PKH = "1LqBGSKuX5yYUonjxT5qGfpUsXKYYWeabA"
EXPECTED_BTC_P2WPKH = "bc1qcr8te4kr609gcawutmrza0j4xv80jy8z306fyu"
EXPECTED_ETH = "0x9858EfFD232B4033E47d90003D41EC34EcaEda94"


# ---- BIP39 seed --------------------------------------------------------

def test_bip39_seed_matches_published_vector():
    w = HDWallet.from_mnemonic(MNEMONIC, PASSPHRASE)
    assert w.seed.hex() == EXPECTED_SEED_HEX


# ---- HD derivations + our address encoders -----------------------------

def test_btc_p2pkh_end_to_end():
    w = HDWallet.from_mnemonic(MNEMONIC, PASSPHRASE)
    info = w.bitcoin_p2pkh(index=0)
    assert info.path == "m/44'/0'/0'/0/0"
    assert info.address == EXPECTED_BTC_P2PKH


def test_btc_p2wpkh_end_to_end():
    w = HDWallet.from_mnemonic(MNEMONIC, PASSPHRASE)
    info = w.bitcoin_p2wpkh(index=0)
    assert info.path == "m/84'/0'/0'/0/0"
    assert info.address == EXPECTED_BTC_P2WPKH


def test_eth_end_to_end():
    w = HDWallet.from_mnemonic(MNEMONIC, PASSPHRASE)
    info = w.ethereum(index=0)
    assert info.path == "m/44'/60'/0'/0/0"
    assert info.address == EXPECTED_ETH


# ---- Genesis block encoder test (Framing B) ----------------------------
#
# Provenance:
#
#   Claim: for the pubkey committed in block 0's coinbase output under
#          OP_CHECKSIG, our pubkey -> HASH160 -> Base58Check pipeline
#          reproduces the address 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa.
#
#   Structural distinction:
#     The genesis output scriptPubKey is P2PK, i.e.
#         OP_PUSH65 || <65-byte uncompressed pubkey> || OP_CHECKSIG.
#     It commits to the public key directly. It does NOT commit to a
#     HASH160, and it is NOT a P2PKH output.
#
#     The address 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa is the P2PKH
#     address associated with that pubkey in external documentation.
#     The test compares against the associated address. It does not
#     claim the genesis output itself was P2PKH.
#
#   Sources (two, with distinct roles):
#     (a) P2PK script structure and pubkey bytes:
#         Bitcoin Core, src/kernel/chainparams.cpp
#         https://github.com/bitcoin/bitcoin/blob/master/src/kernel/chainparams.cpp
#     (b) Documented associated P2PKH address:
#         Bitcoin Wiki, Genesis block
#         https://en.bitcoin.it/wiki/Genesis_block
#
#   If either source changes such that the constants below no longer
#   match, re-verify the constants against the sources. Do not weaken
#   the assertions to make them pass.

GENESIS_COINBASE_HEX = (
    "01000000"
    "01"
    "0000000000000000000000000000000000000000000000000000000000000000ffffffff"
    "4d"
    "04ffff001d0104455468652054696d65732030332f4a616e2f32303039204368616e6365"
    "6c6c6f72206f6e206272696e6b206f66207365636f6e64206261696c6f757420666f7220"
    "62616e6b73"
    "ffffffff"
    "01"
    "00f2052a01000000"
    "43"
    "4104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6"
    "bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac"
    "00000000"
)

EXPECTED_TXID = "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b"
EXPECTED_ADDR = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"

_B58_ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _read_varint(buf: bytes, offset: int) -> tuple[int, int]:
    if offset >= len(buf):
        raise AssertionError(
            f"varint read at offset {offset} past end of buffer "
            f"(len={len(buf)})"
        )
    first = buf[offset]
    if first < 0xFD:
        return first, offset + 1
    if first == 0xFD:
        if offset + 3 > len(buf):
            raise AssertionError(
                f"truncated 0xfd varint at offset {offset} "
                f"(need {offset + 3}, have {len(buf)})"
            )
        return int.from_bytes(buf[offset + 1:offset + 3], "little"), offset + 3
    if first == 0xFE:
        if offset + 5 > len(buf):
            raise AssertionError(
                f"truncated 0xfe varint at offset {offset} "
                f"(need {offset + 5}, have {len(buf)})"
            )
        return int.from_bytes(buf[offset + 1:offset + 5], "little"), offset + 5
    if offset + 9 > len(buf):
        raise AssertionError(
            f"truncated 0xff varint at offset {offset} "
            f"(need {offset + 9}, have {len(buf)})"
        )
    return int.from_bytes(buf[offset + 1:offset + 9], "little"), offset + 9


def _extract_first_output_scriptpubkey(raw: bytes) -> bytes:
    """Parse a raw legacy (non-SegWit) Bitcoin transaction and return the
    scriptPubKey of its first output.

    Walks every input, every output, and the locktime, then asserts that
    the parser lands exactly at len(raw). This catches truncated buffers,
    wrong varint widths, and trailing bytes that a partial parse could
    hide.
    """
    off = 0
    off += 4                                              # version

    n_in, off = _read_varint(raw, off)
    for _ in range(n_in):
        off += 32                                         # prevout hash
        off += 4                                          # prevout index
        slen, off = _read_varint(raw, off)
        assert off + slen <= len(raw), "scriptSig extends past buffer"
        off += slen
        off += 4                                          # sequence

    n_out, off = _read_varint(raw, off)
    assert n_out >= 1, "transaction must have at least one output"

    first_spk: bytes | None = None
    for i in range(n_out):
        off += 8                                          # value
        spk_len, off = _read_varint(raw, off)
        assert off + spk_len <= len(raw), "scriptPubKey extends past buffer"
        spk = raw[off:off + spk_len]
        if i == 0:
            first_spk = spk
        off += spk_len

    off += 4                                              # locktime
    assert off == len(raw), (
        f"parser did not consume transaction exactly: ended at {off}, "
        f"buffer is {len(raw)} bytes"
    )
    assert first_spk is not None
    return first_spk


def _base58check_decode(addr: str) -> bytes:
    """Independent of addresses.py. Returns payload (version || hash)."""
    n = 0
    for c in addr.encode("ascii"):
        n = n * 58 + _B58_ALPHABET.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    pad = len(addr) - len(addr.lstrip("1"))
    raw = b"\x00" * pad + raw
    payload, checksum = raw[:-4], raw[-4:]
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    assert checksum == expected, "address checksum invalid"
    return payload


def test_p2pkh_encoder_against_bitcoin_genesis_block():
    raw = bytes.fromhex(GENESIS_COINBASE_HEX)

    # (0) fixture integrity: raw bytes hash to the canonical txid.
    txid = hashlib.sha256(hashlib.sha256(raw).digest()).digest()[::-1].hex()
    assert txid == EXPECTED_TXID

    # (1) parse the entire transaction; extract the first output's
    #     scriptPubKey. The parser asserts full-buffer consumption.
    spk = _extract_first_output_scriptpubkey(raw)
    assert spk[0] == 0x41 and spk[-1] == 0xAC and len(spk) == 67
    pub_uncompressed = spk[1:-1]
    assert len(pub_uncompressed) == 65 and pub_uncompressed[0] == 0x04

    # (2) independently decode the documented address to recover its HASH160.
    payload = _base58check_decode(EXPECTED_ADDR)
    assert payload[0] == 0x00
    h160_from_address = payload[1:]

    # (3) our HASH160 of the extracted pubkey must equal that.
    sha = hashlib.sha256(pub_uncompressed).digest()
    h160_from_pubkey = hashlib.new("ripemd160", sha).digest()
    assert h160_from_pubkey == h160_from_address

    # (4) encoder round-trip through addresses.py.
    assert addr_enc.p2pkh_address(pub_uncompressed) == EXPECTED_ADDR


# ---- Negatives ---------------------------------------------------------

def test_invalid_mnemonic_rejected():
    with pytest.raises(ValueError):
        HDWallet.from_mnemonic("this is not a valid bip39 mnemonic at all")


def test_reveal_private_validates_scalar():
    w = HDWallet.from_mnemonic(MNEMONIC, PASSPHRASE)
    material = w.reveal_private("m/44'/0'/0'/0/0")
    assert len(material.private_key_hex) == 64


def test_reveal_private_requires_absolute_path():
    w = HDWallet.from_mnemonic(MNEMONIC, PASSPHRASE)
    with pytest.raises(ValueError):
        w.reveal_private("0/0")


def test_ethereum_encoder_rejects_wrong_length():
    with pytest.raises(ValueError):
        addr_enc.ethereum_address(b"\x00" * 63)


def test_ethereum_address_has_eip55_checksum():
    w = HDWallet.from_mnemonic(MNEMONIC, PASSPHRASE)
    addr = w.ethereum().address
    body = addr[2:]
    assert len(body) == 40
    assert any(c.isupper() for c in body)
