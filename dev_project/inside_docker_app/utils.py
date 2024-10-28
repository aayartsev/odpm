import os
import shutil
import json
from urllib.request import urlopen
import zipfile

try:
    from .. import constants
except:
    pass

try:
    from .logger import get_module_logger
except:
    from logger import get_module_logger

_logger = get_module_logger(__name__)

def delete_files_in_directory(directory_path):
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            _logger.warning(f"Failed to delete {file_path}. Reason: {e}")
            exit()

def get_direct_link_to_download_from_yadisk(yadisk_url):
    response = urlopen(constants.YADISK_API_ENDPOINT.format(yadisk_url))
    response_body_in_bytes = response.read()
    response_data = json.loads(response_body_in_bytes.decode("utf-8"))
    link_to_download = response_data["href"]
    return link_to_download

def printProgressBar (iteration, total):
    prefix = ""
    suffix = ""
    decimals = 1
    length = 100
    fill = "█"
    printEnd = "\r"
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + "-" * (length - filledLength)
    print(f"\r{prefix} |{bar}| {percent}% {suffix}", end = printEnd)

def download_file(link_to_download, filepath_to_save):
    with urlopen(link_to_download) as response:
        meta = response.info()
        total_size = dict(meta._headers)["Content-Length"]
        offset = 0
        CHUNK = 16 * 1024
        with open(filepath_to_save, 'wb') as f:
            while True:
                chunk = response.read(CHUNK)
                offset += len(chunk)
                printProgressBar(float(offset), float(total_size))
                if not chunk:
                    break
                f.write(chunk)
    print()

def un_zip_file_to_directory(destination_dir, zip_file):
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        entries = zip_ref.infolist()
        total_entries = entries
        full_size = sum([entry.file_size for entry in total_entries])
        offset = 0
        for entry in total_entries:
            full_file_path = os.path.join(destination_dir, entry.filename)
            if entry.is_dir():
                if not os.path.exists(full_file_path):
                    os.makedirs(full_file_path)
                continue
            with zip_ref.open(entry) as content_from_zip:
                with open(full_file_path, "wb") as file_to_write:
                    while True:
                        b = content_from_zip.read(4096)
                        offset += len(b)
                        printProgressBar(float(offset), full_size)
                        if not b:
                            break
                        file_to_write.write(b)
        print()

def get_free_space(path):
    KB = 1024
    MB = 1024 * KB
    GB = 1024 * MB
    return shutil.disk_usage(path).free / GB