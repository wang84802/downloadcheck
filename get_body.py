import logging
import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()
POSTMAN_API_KEY = os.getenv("POSTMAN_API_KEY")
HEADERS = {"X-API-Key": POSTMAN_API_KEY}


def get_postman_environment_by_name(environment_name):
    """
    取得指定名稱的 Postman Environment
    """
    url = "https://api.getpostman.com/environments"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()  # ✅ 如果不是200會丟出例外
    data = response.json()

    for environment in data["environments"]:
        if environment["name"] == environment_name:
            url = f"https://api.getpostman.com/environments/{environment['uid']}"
            logging.info(f"呼叫 API: {url}")
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()  # ✅ 再次檢查
            return response.json()

def get_post_api_request(collection_name, api_name):
    """
    取得指定 collection 中指定 POST API 的 body
    :param collection_name: Postman Collection 名稱
    :param api_name: POST API 名稱
    :return: dict, 例如 {'mode': 'urlencoded', 'urlencoded': [...]}
    """
    # 先取得所有 collections
    collections_resp = requests.get("https://api.getpostman.com/collections", headers=HEADERS)
    collections_resp.raise_for_status()
    collections_data = collections_resp.json()

    # 找到對應的 collection uid
    collection_uid = None
    for c in collections_data["collections"]:
        if c["name"] == collection_name:
            collection_uid = c["uid"]
            break

    if not collection_uid:
        raise ValueError(f"Collection '{collection_name}' not found")

    # 取得完整 collection 資訊
    collection_resp = requests.get(f"https://api.getpostman.com/collections/{collection_uid}", headers=HEADERS)
    collection_resp.raise_for_status()
    collection_data = collection_resp.json()

    # 遞迴搜尋 item
    def find_api_request(items):
        for item in items:
            # 如果有 request 並且名稱符合
            if "request" in item and item["name"] == api_name:
                # === 在此將 collection data 寫進檔案 ===
                filename = f"{collection_name}_env_request.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(item["request"], f, ensure_ascii=False, indent=4)

                print(f"Collection data 已寫入 {filename}")

                # 下面如你仍要繼續處理 API body，可以接著 return body
                # (此處僅示意)
                return item["request"].get("body", {})
            # 如果有 folder/子 item
            if "item" in item:
                result = find_api_request(item["item"])
                if result:
                    return result
        return None

    body_found = find_api_request(collection_data['collection']['item'])

    if body_found is None:
        raise ValueError(f"API '{api_name}' not found in collection '{collection_name}'")
    return body_found

def body_build(api_body, environment):
    """
    根據 environment 變數替換 api_body 中的 {{variable}} 樣板
    :param api_body: dict, 例如 {'mode': 'urlencoded', 'urlencoded': [...]}
    :param environment: dict, 例如 {'key1': 'value1', 'key2': 'value2'}
    :return: dict, 替換後的 api_body
    """
    if api_body.get('mode') == 'urlencoded':
        for param in api_body.get('urlencoded', []):
            if 'value' in param:
                for key, value in environment.items():
                    placeholder = f"{{{{{key}}}}}"
                    if placeholder in param['value']:
                        param['value'] = param['value'].replace(placeholder, value)
    elif api_body.get('mode') == 'raw':
        raw_value = api_body.get('raw', '')
        for key, value in environment.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in raw_value:
                raw_value = raw_value.replace(placeholder, value)
        api_body['raw'] = raw_value
    return api_body

# ===== 範例使用 =====
if __name__ == "__main__":
    api_body = get_post_api_request("Get_Item_List", "getMakeupItemTree")
    print(api_body)

    # env = get_postman_environment_by_name("YMK_API_URL")
    # env_val = {}
    # count = len(env['environment']['values'])
    # for i in range(count):
    #     env_val[env['environment']['values'][i]['key']] = env['environment']['values'][i]['value'] # url

    # api_body = body_build(api_body, env_val)
    # print(api_body)
    # print(env_val)
    # print("env", env)
