import re

# 假設你的 JSON 是字串（不管是不是 list）
json_text = [
  {
    "id": 1,
    "guid": "AAA-BBB-CCC",
    "name": "item1"
  },
  {
    "id": 2,
    "guid": "DDD-EEE-FFF",
    "name": "item2"
  }
]


# 1. 找出所有 guid
guids = re.findall(r"'guid'\s*:\s*'([^']+)'", json_text.__str__())

# guids = re.findall(r'"guid"\s*:\s*"([^"]+)"', str(json_text))
print(json_text.__str__())
print(guids)


# 2. 移除包含 guid 的整行
# cleaned_json = re.sub(r'.*"guid"\s*:\s*"[^"]+".*\n?', '', json_text, flags=re.MULTILINE)

# print("\n移除後的 JSON：")
# print(cleaned_json)