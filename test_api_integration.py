import os
import pytest
from example_module import (
    get_postman_collection_by_name,
    get_postman_environment_by_name,
    build_api_url,
    fetch_item_list,
    check_guid_loop,
    build_body,
    get_guid_list
)
import logging
from datetime import datetime
import json

@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    # Step 1: 先清除 pytest 預設 handlers
    from logging import root
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    # Step 2: 建立 logs 資料夾
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Step 3: 動態產生 log 檔名
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(log_dir, f"test_log_{timestamp}.log")

    # Step 4: 重新設定 logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    logging.info(f"🔔 Log file created: {log_file}")

class TestPostmanAPI:
    @classmethod
    def setup_class(self):
        self.collection1 = get_postman_collection_by_name("Get_Item_List")
        self.collection2 = get_postman_collection_by_name("Get_Item_Detail")
        self.environment = get_postman_environment_by_name("YMK_API_URL")
        self.env_val = {}
        count = len(self.environment['environment']['values'])
        for i in range(count):
            self.env_val[self.environment['environment']['values'][i]['key']] = self.environment['environment']['values'][i]['value']

        self.domain_list = [""]  # 可擴充多個 domain 做測試

    def build_request_from_postman(self, collection):
        # method
        method = collection["request"]["method"]
        if method.upper() == "POST":
            # headers轉dict
            headers = collection["request"]["header"]
            headers_dict = {h["key"]: h["value"] for h in headers}

            # body轉dict
            body_info = collection["request"]["body"]

            if body_info["mode"] == "urlencoded":
                body_dict = {item["key"]: item["value"] for item in body_info["urlencoded"]}
            else:
                body_dict = {}

            # body replace
            body_dict = build_body(body_dict, self.env_val)

            # raw_url
            raw_url = collection['request']['url']['raw']
            return raw_url, headers_dict, body_dict, method
        else:
            # raw_url
            raw_url = collection['request']['url']['raw']
            return raw_url, {}, {}, method

    def test_guid_loop(self):
        # 每個 domain 做一次測試
        for domain in self.domain_list:
            # detail API
            raw_url_item_detail, headers_item_detail, body_item_detail, method_item_detail = \
                self.build_request_from_postman(self.collection2['collection']['item'][0])
            
            api_url_item_detail = build_api_url(raw_url_item_detail, self.env_val['URL'], self.env_val['service_v2'], domain)

            guid_list = []

            # 每個 collection item 代表一個 list API
            for collection in self.collection1['collection']['item']:
                raw_url_item_list, headers_item_list, body_item_list, method_item_list = \
                    self.build_request_from_postman(collection)
                item_url = build_api_url(raw_url_item_list, self.env_val['URL'], self.env_val['service_v2'], domain)
                list_data = fetch_item_list(item_url, headers_item_list, body_item_list, method_item_list)
                guid_list.extend(get_guid_list(list_data))

            # 去重複
            guid_list = list(set(guid_list))

            check_guid_loop(guid_list, api_url_item_detail, headers_item_detail, body_item_detail, method_item_detail)