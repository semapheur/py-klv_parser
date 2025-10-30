from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from .utils import ber_encode

ValueT = TypeVar("ValueT")


class KLVItem(ABC, Generic[ValueT]):
  """
  Abstract base class for Key-Length-Value (KLV) items.

  KLV encoding uses:
  - Key: identifies the data type
  - Length: BER-encoded length of the value
  - Value: the actual data (can be primitive, KLVTag or KLVSet)
  """

  __slots__ = ("_key", "_raw_value", "value")

  def __init__(self, key: bytes, raw_value: bytes) -> None:
    self._key = key
    self._raw_value = raw_value
    self.value: ValueT

  @property
  def name(self):
    return self.__class__.__name__

  @property
  def length(self) -> bytes:
    return ber_encode(len(self._raw_value))

  def __bytes__(self):
    return self._key + self.length + self._raw_value

  def __len__(self) -> int:
    return len(self._raw_value)

  def __repr__(self) -> str:
    return (
      f"{self.name}(key={self._key.hex()}, length={len(self)}, value={str(self.value)})"
    )

  @abstractmethod
  def __str__(self) -> str:
    pass


class UnknownKLVItem(KLVItem[bytes]):
  """Represents an unknown KLV tag with raw bytes value"""

  def __init__(self, key: bytes, raw_value: bytes):
    super().__init__(key, raw_value)
    self.value = raw_value

  def __str__(self) -> str:
    return f"UnknownKLVItem(key={self._key.hex()}, length={len(self)}, value={str(self.value)})"
