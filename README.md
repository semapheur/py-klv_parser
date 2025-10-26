Example

```python
import klv_parser

klv_data = []
with open("path/to/klv_file.bin", "rb") as f:
  for packet in klv_parser.KLVStreamParser(f):
    metadata = packet.to_dict()
    pprint.pprint(metadata)

```