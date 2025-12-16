"""
Utility helpers for encrypting sensitive fields.
"""

from __future__ import annotations

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken  # type: ignore

from app.config.settings import settings


class CryptoManager:
    """Wrapper around Fernet for field level encryption."""

    def __init__(self) -> None:
        self._fernet = self._create_fernet()

    @staticmethod
    def _create_fernet() -> Fernet:
        key_material = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(key_material)
        return Fernet(key)

    def encrypt_text(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        token = self._fernet.encrypt(value.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt_text(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        try:
            plain = self._fernet.decrypt(value.encode("utf-8"))
            return plain.decode("utf-8")
        except InvalidToken:
            # Already plain text or corrupted; return original to avoid data loss.
            return value


crypto_manager = CryptoManager()
