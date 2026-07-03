from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class StoredReceiptImage:
    storage_key: str
    byte_size: int


class ReceiptImageStorage:
    async def save(self, content: bytes, content_type: str) -> StoredReceiptImage:
        raise NotImplementedError

    async def get(self, storage_key: str) -> bytes:
        raise NotImplementedError

    async def delete(self, storage_key: str) -> None:
        raise NotImplementedError


class LocalReceiptImageStorage(ReceiptImageStorage):
    def __init__(self, root: str) -> None:
        self._root = Path(root)

    async def save(self, content: bytes, content_type: str) -> StoredReceiptImage:
        extension = ".png" if content_type == "image/png" else ".jpg"
        storage_key = f"{uuid4()}{extension}"
        self._root.mkdir(parents=True, exist_ok=True)
        path = self._path_for_key(storage_key)
        path.write_bytes(content)
        return StoredReceiptImage(storage_key=storage_key, byte_size=len(content))

    async def get(self, storage_key: str) -> bytes:
        return self._path_for_key(storage_key).read_bytes()

    async def delete(self, storage_key: str) -> None:
        try:
            os.remove(self._path_for_key(storage_key))
        except FileNotFoundError:
            return

    def _path_for_key(self, storage_key: str) -> Path:
        if Path(storage_key).name != storage_key:
            raise ValueError("Invalid storage key")
        return self._root / storage_key
