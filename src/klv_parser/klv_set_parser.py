from __future__ import annotations
from abc import ABC
from collections import OrderedDict
from datetime import datetime
from pprint import pformat
from typing import Any, Callable, ClassVar, Optional, Type, Union

from .klv_item import KLVItem, UnknownKLVItem
from .klv_stream_parser import KLVParser
from .klv_tag_parser import DecodedValue, KLVTagParser


class KLVSetParser(KLVItem[OrderedDict[bytes, KLVItem[Any]]], ABC):
  key: ClassVar[bytes]
  key_length: ClassVar[int] = 1
  parsers: ClassVar[dict[bytes, Union[Type[KLVSetParser], Type[KLVTagParser]]]] = {}

  def __init__(self, raw_value: bytes) -> None:
    class_key = getattr(self.__class__, "key", None)
    if class_key is None:
      raise ValueError(f"{self.__class__.__name__} must define a 'key' class attribute")

    super().__init__(class_key, raw_value)
    self.value: OrderedDict[bytes, KLVItem[Any]] = OrderedDict()
    self._parse_klv_items()

  def __getitem__(self, key: bytes) -> KLVItem[Any]:
    return self.value[key]

  def _parse_klv_items(self) -> None:
    parser = KLVParser(self._raw_value, self.key_length)
    for key, raw_value in parser:
      parser_cls = self.parsers.get(key)
      if parser_cls is None:
        self.value[key] = UnknownKLVItem(key, raw_value)
        continue

      self.value[key] = parser_cls(raw_value)

  @classmethod
  def add_parser(
    cls, parser_cls: Union[Type[KLVSetParser], Type[KLVTagParser]]
  ) -> Union[Type[KLVSetParser], Type[KLVTagParser]]:
    if not hasattr(parser_cls, "key"):
      raise AttributeError(f"{parser_cls} has no 'key' attribute")

    cls.parsers[parser_cls.key] = parser_cls
    return parser_cls

  def __repr__(self) -> str:
    return pformat(self.value, indent=2)

  def __str__(self) -> str:
    return "\n".join([str(item) for item in self.value.values()])

  def to_dict(
    self,
    datetime_format: Optional[Callable[[datetime], Union[str, int]]] = None,
  ) -> dict[str, DecodedValue]:
    """
    Convert the parsed KLV set into a dictionary of decoded values.

    Args:
      datetime_formatter: Optional callable to format datetime values.
          If provided, it will be applied recursively to all datetime-valued tags.

    Returns:
      dict[str, DecodedValue]: A flattened dictionary mapping tag names to decoded values.
    """

    metadata: dict[str, DecodedValue] = {}

    def recurse(items: OrderedDict[bytes, KLVItem[Any]]):
      for item in items.values():
        if isinstance(item, UnknownKLVItem):
          continue

        if isinstance(item, KLVSetParser):
          recurse(item.value)

        if isinstance(item, KLVTagParser):
          value = item.value
          if datetime_format is not None and isinstance(value, datetime):
            value = datetime_format(value)

          metadata[item.name] = value

    recurse(self.value)
    return metadata

  def print_structure(self) -> None:
    def recurse(items: OrderedDict[bytes, KLVItem[Any]], indent: int = 1):
      for item in items.values():
        print(indent * "\t" + str(type(item)))
        if isinstance(item, KLVSetParser):
          recurse(item.value, indent + 1)
        else:
          print((indent + 1) * "\t" + str(item.value))

    print(str(type(self)))
    recurse(self.value)
