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

    except requests.exceptions.HTTPError as e:
        logging.error(f"❌ API 呼叫失敗，狀態碼: {response.status_code}, 錯誤內容: {e}")
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

    except requests.exceptions.HTTPError as e:
        logging.error(f"❌ API 呼叫失敗，狀態碼: {response.status_code}, 錯誤內容: {e}")
        raise  # 保持原本例外，讓 pytest 判定 FAIL

def get_guid_list(api_data):
    guids = re.findall(r"'guid'\s*:\s*'([^']+)'", api_data.__str__())
    guids = list(set(guids))
    return guids

def check_guid_loop(guid_list, raw_url, headers_dict, body_dict, method):
    logging.info("開始進行 GUID 迴圈檢查...")
    assert guid_list, "api_data is empty or does not exist"

    arr_check_size_item_list = []
    arr_check_md5_item_list = []
    arr_other_error_list = []

    for guid in guid_list:
        logging.info("\n============ 開始檢查 ============\n")
        logging.info(f"GUID: {guid}")

        parsed_url = urlparse(raw_url)
        query_params = parse_qs(parsed_url.query)
        query_params['guids'] = guid
        new_query = urlencode(query_params, doseq=True)
        new_url = urlunparse(parsed_url._replace(query=new_query))

        # call detail API
        if method.upper() == "GET":
            response = requests.get(new_url, headers=headers_dict, params=body_dict)
        elif method.upper() == "POST":
            response = requests.post(new_url, headers=headers_dict, data=body_dict)
        else:
            arr_other_error_list.append(f"❌ 不支援的 HTTP 方法: {method}，GUID: {guid}") # 無法檢查大小
            logging.error(f"❌ 不支援的 HTTP 方法: {method}，GUID: {guid}")
            continue

        if response.status_code != 200:
            arr_other_error_list.append(f"❌ API 回傳非 200 狀態碼: {response.status_code}，GUID: {guid}") # 無法檢查大小
            logging.error(f"❌ API 回傳非 200 狀態碼: {response.status_code}，GUID: {guid}")
            continue

        item_api_data = response.json()
        keys = list(item_api_data.keys())
        item = item_api_data[keys[1]][0]

        # 將欄位名稱轉為小寫以便後續檢查
        item_lower = {k.lower(): v for k, v in item.items()}

        required_fields = ['downloadurl', 'downloadchecksum', 'downloadfilesize']

        # 檢查是否缺任何必要欄位
        missing = [f for f in required_fields if f not in item_lower]
        if missing:
            arr_other_error_list.append(f"❌ API 回傳資料缺少必要欄位: {missing}, {guid}") # 無法檢查大小
            logging.error(f"❌ API 回傳資料缺少必要欄位: {missing}, {guid}")
            # 跳過後面檢查，直接進入下一個 GUID
            continue

        zip_url = item_lower['downloadurl']
        expected_checksum = item_lower['downloadchecksum']
        expected_size_bytes = item_lower['downloadfilesize']

        logging.info(f"ZIP 檔案 URL: {zip_url}")
        logging.info(f"預期檔案大小：{expected_size_bytes} Bytes")
        logging.info(f"預期 MD5 簡碼：{expected_checksum}")

        # ===== 檢查檔案大小 =====
        metadata_response = requests.head(zip_url)
        remote_size_bytes = metadata_response.headers.get('Content-Length')

        if remote_size_bytes:
            remote_size_mb = int(remote_size_bytes) / (1024 * 1024)
            logging.info(f"實際檔案大小：{remote_size_bytes} Bytes ({remote_size_mb:.2f} MB)")
        else:
            arr_other_error_list.append(f"⚠️ 伺服器無 Content-Length : {guid}\nzip_url : {zip_url}") # 無法檢查大小

        if guid == 'thumb_hairband_190104_CNY_look_HD':
            arr_check_size_item_list.append(f"測試: ❌ 檔案大小不符合 : {guid}\nzip_url : {zip_url}")  # 大小不符合
            logging.error(f"測試: ❌ 檔案大小不符合 : {guid} + \n + zip_url : {zip_url}")
        else:
            if remote_size_bytes and int(remote_size_bytes) == expected_size_bytes:
                logging.info('pass check size')
            else:
                arr_check_size_item_list.append(f"測試: ❌ 檔案大小不符合 : {guid}\nzip_url : {zip_url}")  # 大小不符合
                logging.error(f"測試: ❌ 檔案大小不符合 : {guid}\nzip_url : {zip_url}")

        # ===== 驗證檔案完整性 (MD5) ======
        calculated_md5 = calculate_md5_from_url(zip_url)

        if guid == 'pattern_Pignose_190103_3D_ChineseNewYear':
            arr_check_md5_item_list.append(f"測試: ❌ 檔案完整性驗證失敗，MD5 不符合 : {guid}\nzip_url : {zip_url}")  # MD5 不符合
            logging.error(f"測試: ❌ 檔案完整性驗證失敗，MD5 不符合 : {guid}\nzip_url : {zip_url}")
        else:
            logging.info(f"calculated_md5: {calculated_md5}, expected_checksum: {expected_checksum}")
            if calculated_md5 == expected_checksum:
                logging.info('pass check md5')
            else:
                arr_check_md5_item_list.append(f"❌ 檔案完整性驗證失敗，MD5 不符合 : {guid}\nzip_url : {zip_url} \
                                                calculated_md5: {calculated_md5}, expected_checksum: {expected_checksum}")  # MD5 不符合
                logging.error(f"❌ 檔案完整性驗證失敗，MD5 不符合 : {guid}\nzip_url : {zip_url} \
                                                calculated_md5: {calculated_md5}, expected_checksum: {expected_checksum}")


    if arr_check_size_item_list == [] and arr_check_md5_item_list == [] and arr_other_error_list == []:
        logging.info('all correct')
    else:
        logging.error('something error')
        if arr_other_error_list:
            logging.error("有其他錯誤發生:\n" + "\n".join(arr_other_error_list))
        if arr_check_size_item_list:
            logging.error("有項目檔案大小不符合預期:\n" + "\n".join(arr_check_size_item_list))
        if arr_check_md5_item_list:
            logging.error("有項目MD5不符合預期:\n" + "\n".join(arr_check_md5_item_list))

def build_api_url(raw_url, base_url, service_path, domain):
    raw_url = raw_url.replace("{{URL}}", base_url).replace("{{service_v2}}", service_path)
    if domain:
        pattern = r'^(https?://)([^/]+)'
        raw_url = re.sub(pattern, r'\1' + domain, raw_url)
    return raw_url

def fetch_item_list(api_url, headers_dict, body_dict, method):
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