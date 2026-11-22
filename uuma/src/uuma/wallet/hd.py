from __future__ import annotations
import hashlib
from dataclasses import dataclass

from bip_utils import (
    Bip39MnemonicGenerator,
    Bip39WordsNum,
    Bip39SeedGenerator,
    Bip39MnemonicValidator,
    Bip44,
    Bip44Coins,
    Bip44Changes,
    Bip84,
    Bip84Coins,
    Bip32Secp256k1,
)
from ecdsa import SECP256k1

from . import addresses as addr_enc


# Unregistered. Reserved for this prototype. NOT a SLIP-44 entry.
UUMA_EXPERIMENTAL_COIN_TYPE = 9999


@dataclass(frozen=True)
class AddressInfo:
    chain: str
    path: str
    address: str
    public_key_hex: str


@dataclass(frozen=True)
class PrivateKeyMaterial:
    path: str
    private_key_hex: str


class HDWallet:
    def __init__(self, mnemonic: str, passphrase: str = "") -> None:
        if not Bip39MnemonicValidator().IsValid(mnemonic):
            raise ValueError("invalid BIP39 mnemonic")
        self._mnemonic = mnemonic
        self._passphrase = passphrase
        self._seed = Bip39SeedGenerator(mnemonic).Generate(passphrase)

    @classmethod
    def new(cls, strength_bits: int = 128, passphrase: str = "") -> "HDWallet":
        words = {
            128: Bip39WordsNum.WORDS_NUM_12,
            256: Bip39WordsNum.WORDS_NUM_24,
        }[strength_bits]
        return cls(Bip39MnemonicGenerator().FromWordsNumber(words), passphrase)

    @classmethod
    def from_mnemonic(cls, mnemonic: str, passphrase: str = "") -> "HDWallet":
        return cls(mnemonic, passphrase)

    @property
    def seed(self) -> bytes:
        return self._seed

    # ---- public-facing derivations (no secrets returned) ------------

    def bitcoin_p2pkh(self, account: int = 0, change: int = 0, index: int = 0) -> AddressInfo:
        ctx = (
            Bip44.FromSeed(self._seed, Bip44Coins.BITCOIN)
            .Purpose().Coin().Account(account)
            .Change(Bip44Changes.CHAIN_EXT if change == 0 else Bip44Changes.CHAIN_INT)
            .AddressIndex(index)
        )
        pub = ctx.PublicKey().RawCompressed().ToBytes()
        return AddressInfo(
            chain="bitcoin",
            path=f"m/44'/0'/{account}'/{change}/{index}",
            address=addr_enc.p2pkh_address(pub),
            public_key_hex=pub.hex(),
        )

    def bitcoin_p2wpkh(self, account: int = 0, change: int = 0, index: int = 0) -> AddressInfo:
        ctx = (
            Bip84.FromSeed(self._seed, Bip84Coins.BITCOIN)
            .Purpose().Coin().Account(account)
            .Change(Bip44Changes.CHAIN_EXT if change == 0 else Bip44Changes.CHAIN_INT)
            .AddressIndex(index)
        )
        pub = ctx.PublicKey().RawCompressed().ToBytes()
        return AddressInfo(
            chain="bitcoin",
            path=f"m/84'/0'/{account}'/{change}/{index}",
            address=addr_enc.p2wpkh_address(pub),
            public_key_hex=pub.hex(),
        )

    def ethereum(self, account: int = 0, change: int = 0, index: int = 0) -> AddressInfo:
        ctx = (
            Bip44.FromSeed(self._seed, Bip44Coins.ETHEREUM)
            .Purpose().Coin().Account(account)
            .Change(Bip44Changes.CHAIN_EXT if change == 0 else Bip44Changes.CHAIN_INT)
            .AddressIndex(index)
        )
        raw_uncompressed = ctx.PublicKey().RawUncompressed().ToBytes()
        if len(raw_uncompressed) == 65 and raw_uncompressed[0] == 0x04:
            pub = raw_uncompressed[1:]
        else:
            pub = raw_uncompressed
        return AddressInfo(
            chain="ethereum",
            path=f"m/44'/60'/{account}'/{change}/{index}",
            address=addr_enc.ethereum_address(pub),
            public_key_hex=pub.hex(),
        )

    def uuma_experimental(self, account: int = 0, index: int = 0) -> AddressInfo:
        path = f"m/44'/{UUMA_EXPERIMENTAL_COIN_TYPE}'/{account}'/0/{index}"
        root = Bip32Secp256k1.FromSeed(self._seed)
        child = root.DerivePath(path)
        pub = child.PublicKey().RawCompressed().ToBytes()
        uma = "UMA" + hashlib.blake2b(pub, digest_size=20).hexdigest().upper()
        return AddressInfo(
            chain="uuma-experimental",
            path=path,
            address=uma,
            public_key_hex=pub.hex(),
        )

    # ---- explicit private key access -------------------------------

    def reveal_private(self, path: str) -> PrivateKeyMaterial:
        if not path.startswith("m/"):
            raise ValueError("path must be absolute (start with m/)")
        root = Bip32Secp256k1.FromSeed(self._seed)
        child = root.DerivePath(path)
        priv = child.PrivateKey().Raw().ToBytes()
        scalar = int.from_bytes(priv, "big")
        n = SECP256k1.order
        if not (1 <= scalar < n):
            raise ValueError("derived scalar is not a valid secp256k1 value")
        return PrivateKeyMaterial(path=path, private_key_hex=priv.hex())
