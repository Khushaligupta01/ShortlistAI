from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.core.config import Settings, settings


class StorageError(Exception):
    """Base exception for storage errors."""
    pass


class StoragePathTraversalError(StorageError):
    """Raised when a storage path attempts directory traversal."""
    pass


class StorageFileNotFoundError(StorageError):
    """Raised when a requested file does not exist in storage."""
    pass


@runtime_checkable
class StorageService(Protocol):
    """Abstract interface for private document storage."""

    async def save_file(
        self,
        organization_id: uuid.UUID,
        file_bytes: bytes,
        extension: str,
    ) -> str:
        """
        Save file bytes into private storage.
        Returns a safe internal storage key.
        """
        ...

    async def get_file(self, storage_key: str) -> bytes:
        """
        Retrieve file bytes by storage key.
        Raises StorageFileNotFoundError if not found.
        """
        ...

    async def delete_file(self, storage_key: str) -> bool:
        """Delete file by storage key. Returns True if deleted."""
        ...

    async def file_exists(self, storage_key: str) -> bool:
        """Check if file exists in storage."""
        ...


class LocalStorageService:
    """
    Local filesystem implementation of StorageService.
    Stores files securely outside public web directories with strict traversal checks.
    """

    def __init__(self, root_dir: str | Path | None = None) -> None:
        raw_root = root_dir or settings.STORAGE_LOCAL_ROOT
        self._root = Path(raw_root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve_and_verify_path(self, storage_key: str) -> Path:
        # Sanitize storage key: remove leading slashes and normpath
        clean_key = os.path.normpath(storage_key).lstrip("\\/.")
        resolved = (self._root / clean_key).resolve()

        # Strict boundary check against path traversal
        if not str(resolved).startswith(str(self._root)):
            raise StoragePathTraversalError(
                f"Directory traversal detected for storage key: {storage_key}"
            )
        return resolved

    async def save_file(
        self,
        organization_id: uuid.UUID,
        file_bytes: bytes,
        extension: str,
    ) -> str:
        ext = extension.lower().strip()
        if not ext.startswith("."):
            ext = f".{ext}"

        now = datetime.now(timezone.utc)
        file_id = uuid.uuid4()
        # Internal key: {org_id}/{year}/{month}/{file_id}{ext}
        relative_key = f"{organization_id}/{now.year:04d}/{now.month:02d}/{file_id}{ext}"
        target_path = self._resolve_and_verify_path(relative_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        target_path.write_bytes(file_bytes)
        return relative_key.replace("\\", "/")

    async def get_file(self, storage_key: str) -> bytes:
        target_path = self._resolve_and_verify_path(storage_key)
        if not target_path.exists() or not target_path.is_file():
            raise StorageFileNotFoundError(f"File not found for key: {storage_key}")
        return target_path.read_bytes()

    async def delete_file(self, storage_key: str) -> bool:
        target_path = self._resolve_and_verify_path(storage_key)
        if target_path.exists() and target_path.is_file():
            target_path.unlink()
            return True
        return False

    async def file_exists(self, storage_key: str) -> bool:
        try:
            target_path = self._resolve_and_verify_path(storage_key)
            return target_path.exists() and target_path.is_file()
        except StoragePathTraversalError:
            return False


_storage_instance: StorageService | None = None


def get_storage_service(config: Settings | None = None) -> StorageService:
    global _storage_instance
    if _storage_instance is None:
        cfg = config or settings
        if cfg.STORAGE_TYPE.lower() == "local":
            _storage_instance = LocalStorageService(cfg.STORAGE_LOCAL_ROOT)
        else:
            raise ValueError(f"Unsupported STORAGE_TYPE: {cfg.STORAGE_TYPE}")
    return _storage_instance

