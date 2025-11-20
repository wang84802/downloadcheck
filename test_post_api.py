import requests
from dotenv import load_dotenv
import os
import hashlib
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import logging

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = "your_postman_api_key"
headers = {
    "X-API-Key": os.getenv("POSTMAN_API_KEY")
}

url = "https://api.getpostman.com/collections"
response = requests.get(url, headers=headers)
response.raise_for_status()  # ✅ 如果不是200會丟出例外
data  = response.json()

collection_name = "Get_Item_List"

for collection in data["collections"]:
    if collection["name"] == collection_name:
        url = f"https://api.getpostman.com/collections/{collection['uid']}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # ✅ 再次檢查
        return_data = response.json()
        print(return_data)