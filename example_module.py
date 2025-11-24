from itertools import count
import requests
from dotenv import load_dotenv
import os
import hashlib
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import logging
import re
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = "your_postman_api_key"
headers = {
    "X-API-Key": os.getenv("POSTMAN_API_KEY")
}

def get_postman_collection_by_name(collection_name):
    try:
        url = "https://api.getpostman.com/collections"
        logging.info(f"呼叫 API: {url}")
        response = requests.get(url, headers=headers)
        logging.info(f"收到 HTTP 狀態碼: {response.status_code}")
        response.raise_for_status()  # ✅ 如果不是200會丟出例外
        data  = response.json()
        logging.info("✅ API 呼叫成功")

        for collection in data["collections"]:
            if collection["name"] == collection_name:
                url = f"https://api.getpostman.com/collections/{collection['uid']}"
                logging.info(f"呼叫 API: {url}")
                response = requests.get(url, headers=headers)
                logging.info(f"收到 HTTP 狀態碼: {response.status_code}")
                response.raise_for_status()  # ✅ 再次檢查
                return_data = response.json()
                logging.info("✅ API 呼叫成功")
                return return_data
        assert False, f"Collection '{collection_name}' not found"  # ✅ 沒找到也fail

    except Exception as e:
        logging.error(f"❌ API 呼叫失敗, 錯誤內容: {e}")
        raise  # 保持原本例外，讓 pytest 判定 FAIL

def get_postman_environment_by_name(environment_name):
    try:
    # 取得所有 Environments
        url = "https://api.getpostman.com/environments"
        logging.info(f"呼叫 API: {url}")
        response = requests.get(url, headers=headers)
        logging.info(f"收到 HTTP 狀態碼: {response.status_code}")
        response.raise_for_status()  # ✅ 如果不是200會丟出例外
        data = response.json()

        for environment in data["environments"]:
            if environment["name"] == environment_name:
                url = f"https://api.getpostman.com/environments/{environment['uid']}"
                logging.info(f"呼叫 API: {url}")
                response = requests.get(url, headers=headers)
                response.raise_for_status()  # ✅ 再次檢查
                return response.json()
        assert False, f"Environment '{environment_name}' not found"  # ✅ 沒找到也fail

    except Exception as e:
        logging.error(f"❌ API 呼叫失敗, 錯誤內容: {e}")
        raise  # 保持原本例外，讓 pytest 判定 FAIL

def get_guid_list(api_data):
    guids = re.findall(r"'guid'\s*:\s*'([^']+)'", api_data.__str__())
    guids = list(set(guids))
    return guids

def check_guid_loop(guid_list, raw_url, headers_dict, body_dict, method):
    domain = re.findall(r'^https://[^/]+', raw_url)
    logging.info(f"開始進行 domain 迴圈檢查 : {domain[0]}")

    assert guid_list, "api_data is empty or does not exist"

    arr_check_size_item_list = []
    arr_check_md5_item_list = []
    arr_missing_field_list = []
    arr_other_error_list = []
    arr_success_list = []

    for guid in guid_list:

        parsed_url = urlparse(raw_url)
        query_params = parse_qs(parsed_url.query)
        query_params['guids'] = guid
        new_query = urlencode(query_params, doseq=True)
        new_url = urlunparse(parsed_url._replace(query=new_query))

        # call detail API
        if guid == "161101_modeliste":
            arr_other_error_list.append(f"測試❌ 不支援的 HTTP 方法: {method}，GUID: {guid}")
            continue
        if method.upper() == "GET":
            response = requests.get(new_url, headers=headers_dict, params=body_dict)
        elif method.upper() == "POST":
            response = requests.post(new_url, headers=headers_dict, data=body_dict)
        else:
            arr_other_error_list.append(f"❌ 不支援的 HTTP 方法: {method}，GUID: {guid}")
            continue
        
        if guid == "store_necklace_20150522_03":
            arr_other_error_list.append(f"測試❌ API 回傳非 200 狀態碼: {response.status_code}，GUID: {guid}")
            continue
        else:
            if response.status_code != 200:
                arr_other_error_list.append(f"❌ API 回傳非 200 狀態碼: {response.status_code}，GUID: {guid}")
                continue

        item_api_data = response.json()
        keys = list(item_api_data.keys())
        item = item_api_data[keys[1]][0]

        item_lower = {k.lower(): v for k, v in item.items()}

        required_fields = ['downloadurl', 'downloadchecksum', 'downloadfilesize']
        missing = [f for f in required_fields if f not in item_lower]

        if missing:
            arr_missing_field_list.append(
                f"- {guid} (缺少欄位: {', '.join(missing)})"
            )
            continue

        zip_url = item_lower['downloadurl']
        expected_checksum = item_lower['downloadchecksum']
        expected_size_bytes = item_lower['downloadfilesize']

        # ===== 檢查檔案大小 =====
        metadata_response = requests.head(zip_url)
        remote_size_bytes = metadata_response.headers.get('Content-Length')

        if not remote_size_bytes:
            arr_other_error_list.append(f"⚠️ 伺服器無 Content-Length : {guid}\nURL : {zip_url}")

        # 檔案大小錯誤
        if guid == 'thumb_hairband_190104_CNY_look_HD':
            arr_check_size_item_list.append(
                f"測試- {guid}\n  URL: {zip_url}\n  Expected: {expected_size_bytes}\n  Actual: {remote_size_bytes}"
            )  # 大小不符合
        else:
            if not remote_size_bytes or int(remote_size_bytes) != expected_size_bytes:
                arr_check_size_item_list.append(
                    f"- {guid}\n  URL: {zip_url}\n  Expected: {expected_size_bytes}\n  Actual: {remote_size_bytes}"
                )

        # ===== MD5 驗證 =====
        calculated_md5 = calculate_md5_from_url(zip_url)

        if guid == 'pattern_Pignose_190103_3D_ChineseNewYear':
            arr_check_md5_item_list.append(
                f"測試- {guid}\n  URL: {zip_url}\n  Expected: {expected_checksum}\n  Actual: {calculated_md5}"
            )
        else:
            if calculated_md5 != expected_checksum:
                arr_check_md5_item_list.append(
                    f"- {guid}\n  URL: {zip_url}\n  Expected: {expected_checksum}\n  Actual: {calculated_md5}"
                )

        # 全部成功才加入成功清單
        if (remote_size_bytes and int(remote_size_bytes) == expected_size_bytes and
                calculated_md5 == expected_checksum):
            arr_success_list.append(guid)

    # ============================================================
    #                ★★★★★ Final Report ★★★★★
    # ============================================================

    logging.info("\n\n============ 最終測試報告 ============\n")

    # ⚠ 缺少欄位
    logging.info("\n## ⚠ 缺少必要欄位\n" +
                 ("\n".join(arr_missing_field_list) if arr_missing_field_list else "（無）"))

    # ❌ Size mismatch
    logging.info("\n## ❌ 檔案大小不符\n" +
                 ("\n".join(arr_check_size_item_list) if arr_check_size_item_list else "（無）"))

    # ❌ MD5 mismatch
    logging.info("\n## ❌ MD5 不符合\n" +
                 ("\n".join(arr_check_md5_item_list) if arr_check_md5_item_list else "（無）"))

    # 其他錯誤
    logging.info("\n## ⚠ 其他錯誤\n" +
                 ("\n".join(arr_other_error_list) if arr_other_error_list else "（無）"))

    # Summary
    total = len(guid_list)
    success = len(arr_success_list)
    missing = len(arr_missing_field_list)
    size_err = len(arr_check_size_item_list)
    md5_err = len(arr_check_md5_item_list)
    other_err = len(arr_other_error_list)

    logging.info("\n============ Summary ============\n"
                 f"✔ 成功: {success}\n"
                 f"⚠ 缺少欄位: {missing}\n"
                 f"❌ Size mismatch: {size_err}\n"
                 f"❌ MD5 mismatch: {md5_err}\n"
                 f"⚠ 其他錯誤: {other_err}\n"
                 f"總測試項目數: {total}\n"
                 "=================================\n")

def build_api_url(raw_url, base_url, service_path, domain):
    raw_url = raw_url.replace("{{URL}}", base_url).replace("{{service_v2}}", service_path)
    if domain:
        pattern = r'^(https://)([^/]+)'
        raw_url = re.sub(pattern, domain, raw_url)
    return raw_url

def fetch_item_list(api_url, headers_dict, body_dict, method):
    try:
        logging.info(f"fetch 呼叫 API: {api_url} with method: {method}")
        if method.upper() == "GET":
            response = requests.get(api_url, headers=headers_dict, params=body_dict)
            response.raise_for_status()
            return response.json()
        elif method.upper() == "POST":
            response = requests.post(api_url, headers=headers_dict, data=body_dict)
            response.raise_for_status()
            return response.json()
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    except Exception as e:
        logging.error(f"❌ API 呼叫失敗, 錯誤內容: {e}")
        raise  # 保持原本例外，讓 pytest 判定 FAIL

def calculate_md5_from_url(url):
    hash_md5 = hashlib.md5()
    with requests.get(url, stream=True) as r:
        for chunk in r.iter_content(chunk_size=8192):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def build_body(body_dict, env_dict):
    new_body = {}
    for key, val in body_dict.items():
        # 如果 value 是 {{variable}}
        if isinstance(val, str) and val.startswith("{{") and val.endswith("}}"):
            var_name = val[2:-2]   # 去掉 {{}}
            new_body[key] = env_dict.get(var_name, val)
        else:
            new_body[key] = val
    return new_body