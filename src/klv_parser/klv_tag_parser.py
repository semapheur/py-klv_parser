from abc import ABC, abstractmethod
from datetime import datetime
from typing import ClassVar, Optional, TypeAlias, Union

from klv_item import KLVItem
from utils import (
  bytes_to_datetime,
  bytes_to_float,
  bytes_to_hexstr,
  bytes_to_str,
)

DecodedValue: TypeAlias = Union[bytes, int, float, str, datetime, None]


class BaseValue(ABC):
  __slots__ = ("raw_value",)

  def __init__(self, raw_value: bytes) -> None:
    self.raw_value = raw_value

  def __bytes__(self) -> bytes:
    return self.raw_value

  @abstractmethod
  def decode(self) -> DecodedValue:
    pass

  @abstractmethod
  def __str__(self) -> str:
    pass


class KLVTagParser(KLVItem[DecodedValue], ABC):
  """
  Abstract base class for KLV tag parsers.
  """

  key: bytes
  label: ClassVar[str]
  TAG: ClassVar[int]
  LDSName: ClassVar[str]
  ESDName: ClassVar[str]
  UDSName: ClassVar[str]

  def __init__(self, value_wrapper: BaseValue):
    super().__init__(self.key, value_wrapper.raw_value)
    self.value: DecodedValue = value_wrapper.decode()

  def __str__(self) -> str:
    return f"{self.name}(value={self.value!r})"

  def __repr__(self) -> str:
    return str(self)


class BytesValue(BaseValue):
  def decode(self) -> bytes:
    return self.raw_value

  def __str__(self) -> str:
    return bytes_to_hexstr(self.raw_value, start="0x", sep="")


class BytesTagParser(KLVTagParser, ABC):
  def __init__(self, value: bytes):
    super().__init__(BytesValue(value))


class DateTimeValue(BaseValue):
  def decode(self) -> datetime:
    return bytes_to_datetime(self.raw_value)

  def __str__(self) -> str:
    datetime_decoded = self.decode()
    return datetime_decoded.isoformat(sep=" ")


class DateTimeTagParser(KLVTagParser, ABC):
  def __init__(self, value: bytes):
    super().__init__(DateTimeValue(value))


class StringValue(BaseValue):
  def decode(self) -> str:
    return bytes_to_str(self.raw_value)

  def __str__(self) -> str:
    return self.decode()


class StringTagParser(KLVTagParser, ABC):
  def __init__(self, value: bytes):
    super().__init__(StringValue(value))


class MappedValue(BaseValue):
  __slots__ = BaseValue.__slots__ + ("_domain", "_range", "_error")

  def __init__(
    self,
    raw_value: bytes,
    _domain: tuple[int, int],
    _range: tuple[float, float],
    _error: Optional[int],
  ):
    self._domain = _domain
    self._range = _range
    self._error = _error
    self.raw_value = raw_value

  def decode(self) -> Optional[float]:
    return bytes_to_float(self.raw_value, self._domain, self._range, self._error)

  def __str__(self) -> str:
    float_decoded = self.decode()
    if float_decoded is None:
      return ""

    return format(float_decoded)

  def __float__(self):
    return self.decode()


class MappedTagParser(KLVTagParser, ABC):
  _domain: ClassVar[tuple[int, int]]
  _range: ClassVar[tuple[float, float]]
  _error: ClassVar[int | None] = None

  def __init__(self, value: bytes):
    super().__init__(MappedValue(value, self._domain, self._range, self._error))
