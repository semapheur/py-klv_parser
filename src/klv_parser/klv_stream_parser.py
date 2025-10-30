from __future__ import annotations

from io import BytesIO, IOBase

from typing import BinaryIO, ClassVar, Iterator, Type, TYPE_CHECKING, Union

from .klv_item import UnknownKLVItem
from .utils import bytes_to_int

if TYPE_CHECKING:
  from .klv_set_parser import KLVSetParser


class KLVParser(Iterator[tuple[bytes, bytes]]):
  """
  Iterator that yields (key, value) pairs parsed from an SMPTE ST 336 source.

  Each record in the stream consists of:
    - A fixed-length key (`key_length` bytes)
    - A BER-encoded length field
    - A value of the given length
  """

  __slots__ = ("source", "key_length")

  def __init__(self, source: Union[bytes, bytearray, BinaryIO], key_length: int):
    if key_length < 0:
      raise ValueError("key_length must be a non-negative integer")

    if isinstance(source, (bytes, bytearray)):
      self.source: BinaryIO = BytesIO(source)
    elif isinstance(source, IOBase):
      self.source = source
    else:
      raise TypeError("source must be bytes or bytearray, or a binary file-like object")

    self.key_length = key_length

  def __iter__(self) -> KLVParser:
    return self

  def __next__(self) -> tuple[bytes, bytes]:
    key = self._read(self.key_length)
    length = self._read_ber_length()
    value = self._read(length)
    return key, value

  def _read_ber_length(self) -> int:
    first_byte = self.source.read(1)
    if not first_byte:
      raise StopIteration("Unexpected end of stream")

    byte_value = first_byte[0]

    if byte_value < 128:  # BER short form
      return byte_value

    # BER long form
    num_bytes = byte_value - 128
    if num_bytes == 0:
      raise ValueError("Invalid BER long form with zero length")

    length_bytes = self._read(num_bytes)
    if len(length_bytes) != num_bytes:
      raise StopIteration("Unexpected end of stream")

    return bytes_to_int(length_bytes)

  def _read(self, size: int) -> bytes:
    if size == 0:
      return b""

    data = self.source.read(size)
    if len(data) != size:
      raise StopIteration("Unexpected end of stream")

    return data


class KLVStreamParser:
  """
  A parser for KLV streams.

  A KLV stream consists of a sequence of records, each consisting of a
  fixed-length key, a BER-encoded length field, and a value of the given
  length.

  This class provides a way to iterate over the records in the stream, and
  optionally register parsers for specific key types.

  Attributes:
    iter_stream (KLVParser): The KLV parser used to iterate over the stream.
  """

  __slots__ = ("iter_stream",)
  parsers: ClassVar[dict[bytes, Type[KLVSetParser]]] = {}

  def __init__(
    self, source: Union[bytes, bytearray, BinaryIO], key_length: int = 16
  ) -> None:
    """
    Initialize a KLV stream parser.

    Args:
      source (Union[bytes, bytearray, BinaryIO]): The source of the KLV stream.
      key_length (int, optional): The length of the keys in the stream. Defaults to 16.
    """
    self.iter_stream = KLVParser(source, key_length)

  def __iter__(self) -> KLVStreamParser:
    return self

  def __next__(self) -> Union[KLVSetParser, UnknownKLVItem]:
    key, value = next(self.iter_stream)
    parser_cls = self.parsers.get(key)
    if parser_cls is None:
      return UnknownKLVItem(key, value)

    return parser_cls(value)

  @classmethod
  def add_parser(cls, parser_cls: Type[KLVSetParser]) -> Type[KLVSetParser]:
    """
    Register a parser for a specific key type.

    Args:
      parser_cls (Type[KLVSetParser]): The parser to register.

    Returns:
      Type[KLVSetParser]: The registered parser.
    """
    if not hasattr(parser_cls, "key"):
      raise AttributeError(f"{parser_cls.name} has no 'key' attribute")

    cls.parsers[parser_cls.key] = parser_cls
    return parser_cls
