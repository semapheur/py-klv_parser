from datetime import datetime, timezone
from struct import pack
from typing import Optional, Union


def bytes_to_int(value: bytes, signed: bool = False) -> int:
  return int.from_bytes(value, "big", signed=signed)


def int_to_bytes(value: int, length: int = 1, signed: bool = False) -> bytes:
  return int(value).to_bytes(length, byteorder="big", signed=signed)


def linear_map(
  src_value: float, src_domain: tuple[float, float], dst_range: tuple[float, float]
) -> float:
  """
  Maps a given value from its source range to the destination range.

  Args:
    src_value (float): The value to be mapped.
    src_domain (tuple[float, float]): A tuple containing the minimum and
      maximum values of the source range.
    dst_range (tuple[float, float]): A tuple containing the minimum and
      maximum values of the destination range.

  Returns:
    float: The mapped value.

  Raises:
    ValueError: If the source value is outside the source range or the
      mapped value is outside the destination range.
  """

  src_min, src_max, dst_min, dst_max = src_domain + dst_range

  if not (src_min <= src_value <= src_max):
    raise ValueError(f"Value must be between {src_min} and {src_max}")

  slope = (dst_max - dst_min) / (src_max - src_min)
  dst_value = slope * (src_value - src_min) + dst_min

  if not (dst_min <= dst_value <= dst_max):
    raise ValueError(f"Value must be between {dst_min} and {dst_max}")

  return dst_value


def bytes_to_float(
  value: bytes,
  _domain: tuple[int, int],
  _range: tuple[float, float],
  _error: Optional[int] = None,
) -> Union[float, None]:
  src_value = int.from_bytes(value, byteorder="big", signed=(min(_domain) < 0))
  if src_value == _error:
    return None

  return linear_map(src_value, _domain, _range)


def float_to_bytes(
  value: Optional[float],
  _domain: tuple[int, int],
  _range: tuple[float, float],
  _error: Optional[int] = None,
) -> Union[bytes, None]:
  src_domain, dst_range = _range, _domain
  _, _, dst_min, dst_max = src_domain + dst_range
  length = int((dst_max - dst_min - 1).bit_length() / 8)
  if value is None:
    if _error is None:
      raise ValueError("Error value must be specified if value is None")
    dst_value = _error
  else:
    dst_value = round(linear_map(value, src_domain, dst_range))

  return dst_value.to_bytes(length, byteorder="big", signed=(dst_min < 0))


def hexstr_to_bytes(value: str) -> bytes:
  return bytes.fromhex("".join(filter(str.isalnum, value)))


def bytes_to_hexstr(value: bytes, start: str = "", sep: str = " ") -> str:
  return start + sep.join(["{:02X}".format(byte) for byte in bytes(value)])


def ber_encode(value: int) -> bytes:
  """
  Encode an integer using BER (Basic Encoding Rules) length encoding.

  Short form (1 byte):
    0x00–0x7F → single byte containing the value

  Long form (N+1 bytes):
    0x80 | N  → indicates N bytes follow that encode the length
    Next N bytes → big-endian representation of the length value

  Args:
    value (int): Non-negative integer to encode.

  Returns:
    bytes: BER-encoded representation of the integer length.

  Raises:
    ValueError: If value is negative.
  """
  if value < 0:
    raise ValueError("value must be non-negative")

  if value < 128:  # BER short form
    return int_to_bytes(value)

  # BER long form
  num_bytes = (value.bit_length() + 7) // 8
  prefix = int_to_bytes(0x80 | num_bytes)
  return prefix + int_to_bytes(value, num_bytes)


def datetime_to_bytes(value: datetime) -> bytes:
  return pack(">Q", int(value.timestamp() * 1e6))


def bytes_to_datetime(value: bytes) -> datetime:
  return datetime.fromtimestamp(bytes_to_int(value) / 1e6, tz=timezone.utc)


def bytes_to_str(value: bytes) -> str:
  return value.decode("utf-8")


def str_to_bytes(value: str) -> bytes:
  return value.encode("utf-8")


def ber_decode(value: bytes) -> int:
  """
  Decode a BER-encoded length field (per SMPTE ST 336 / ASN.1 BER rules).

  Short form (1 byte): if first < 128
    [ length ]

  Long form (N+1 bytes): if first >= 128
    [ 0x80 | N ] [ length in N bytes, big endian ]

  Args:
    value (bytes): Byte sequence containing a BER-encoded integer.

  Returns:
    int: The decoded integer length.

  Raises:
    ValueError: if the encoding is invalid or incomplete.
  """

  if bytes_to_int(value) < 128:  # BER short form
    if len(value) > 1:
      raise ValueError("Invalid BER short form with more than one byte")

    return bytes_to_int(value)

  # BER long form
  if len(value) != (value[0] - 127):
    raise ValueError("Invalid BER long form with incorrect length")

  return bytes_to_int(value[1:])
