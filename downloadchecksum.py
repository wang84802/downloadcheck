import hashlib
import requests

def calculate_md5(url):
    hash_md5 = hashlib.md5()
    with requests.get(url, stream=True) as r:
        for chunk in r.iter_content(chunk_size=8192):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

a = calculate_md5("https://cdn.perfectcorp.com/store/makeupstore/MSR/PFA200408-0040/3/thumb_hairband_190819_Furfur_Look_13.zip")

print(a)