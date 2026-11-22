"""Symmetric encryption helper used by the zero-trust layer.

Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>

Uses Fernet (AES-128-CBC + HMAC). The key comes from ``COVENANT_ENCRYPTION_KEY``
(urlsafe base64, 32 bytes); if unset an ephemeral per-process key is generated,
so encrypted data does not survive a restart - set the variable in production.
"""
import os
from typing import Optional

from cryptography.fernet import Fernet


class EncryptionManager:
    def __init__(self, key: Optional[bytes] = None):
        env = os.environ.get("COVENANT_ENCRYPTION_KEY")
        self._fernet = Fernet(key or (env.encode() if env else Fernet.generate_key()))

    def encrypt(self, data: str) -> str:
        return self._fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()
