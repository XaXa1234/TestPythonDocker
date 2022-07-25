from seleniumwire import webdriver
from seleniumwire.utils import decode  as sw_decode
import logging
import json, os, shutil
from pathlib import Path

logging.getLogger().setLevel(logging.INFO)
logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
def logger(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        log = logging.getLogger(fn.__name__)
        log.info('About to run %s' % fn.__name__)
        out = fn(*args, **kwargs)
        log.info('Done running %s' % fn.__name__)
        return out
    return wrapper

def filesize(size: int) -> str:
    for unit in ("B", "K", "M", "G", "T"):
        if size < 1024:
            break
        size /= 1024
    return f"{size:.1f}{unit}"  
def get_size(folder: str) -> int:
    return filesize(sum(p.stat().st_size for p in Path(folder).rglob('*')))

def get_subfolders(folder):
    list_subfolders_with_paths = [f.path for f in os.scandir(folder) if f.is_dir()]
    return list_subfolders_with_paths

URL_ARG = 'url'
HEADERS_ARG = 'headers'
USER_DATA_TEMPDIR = '/tmp/datauserdir'
DATA_PATH_TEMPDIR = '/tmp/datapath'
DISK_CACHE_TEMPDIR = '/tmp/diskcachedir'
SELENIUMWIRE_TMPDIR = '/tmp/seleniumwire'

@logger
def get_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("disable-infobars")
    chrome_options.add_argument('--window-size=1280x1696')
    chrome_options.add_argument('--hide-scrollbars')
    chrome_options.add_argument('--enable-logging')
    chrome_options.add_argument('--log-level=0')
    chrome_options.add_argument('--v=99')
    chrome_options.add_argument('--single-process')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument(f"--user-data-dir={USER_DATA_TEMPDIR}")
    chrome_options.add_argument(f"--data-path={DATA_PATH_TEMPDIR}")
    chrome_options.add_argument(f"--disk-cache-dir={DISK_CACHE_TEMPDIR}")
    chrome_options.add_argument("--lang=en_US")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36")
    chrome_options.binary_location = '/opt/chrome/chrome'
    return chrome_options

@logger
def get_selenium_wire_options():
	options = {'request_storage': SELENIUMWIRE_TMPDIR}
	return options

@logger
def delete_temp_folder():
    for root, dirs, files in os.walk('/tmp', topdown=False):
        for name in files:
            try:
                os.remove(os.path.join(root, name))
            except Exception:
                pass
        for name in dirs:
            try:
                os.rmdir(os.path.join(root, name))
            except Exception:
                pass
@logger
def requ_interceptor_with_headers(headers):
	def interceptor(request):
		for key, value in headers.items():
			if key in request.headers:
				del request.headers[key]
			request.headers[key]=value
	return interceptor   
@logger
def get_chrome():
   options = get_chrome_options()
   seleniumewire_options = get_selenium_wire_options()
   chrome = webdriver.Chrome("/opt/chromedriver", chrome_options=options, seleniumwire_options=seleniumewire_options) 
   return chrome
@logger
def get_url(chrome, url):
    chrome.get(url)
@logger
def get_data_from_chrome(chrome):
    for request in chrome.requests:
        data = sw_decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity')) 
    return data
@logger
def close_chrome(chrome):
    chrome.get("about:blank")
    chrome.delete_all_cookies()
    # chrome.execute_script('localStorage.clear();')
    chrome.quit()
@logger
def function_handler(event, context):
    logging.info(f"lambda invoked with event: {event}")
    logging.debug(f'Size tmp folder:{get_size("/tmp")}')
    logging.debug(f'Subfolders tmp folder:{get_subfolders("/tmp")}')
    if URL_ARG not in event:
        logging.error(f'{URL_ARG} not present')
        raise ValueError(f"{URL_ARG} must be present in the event")
    try:
        chrome = get_chrome()
        logging.info(f'fetching url: {event[URL_ARG]}')
        url = event[URL_ARG]
        if HEADERS_ARG in event:
            interceptor = requ_interceptor_with_headers(event[HEADERS_ARG])
            chrome.request_interceptor = interceptor
        get_url(chrome,url)
        data = get_data_from_chrome(chrome)
        close_chrome(chrome)
    except Exception as e:
        logging.error(f"Error happened: {e}")
    finally:
        delete_temp_folder()
    return data
