import os
import json
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

COOKIE_FILE_PATH = "/Users/hedongwei/Documents/Work/PycharmProjects/LocalAssistant/backend/cookies.json"

def get_cookies_from_browser():
    """
    从浏览器重新获取 Cookie，仅提取 `atlassian.xsrf.token` 和 `JSESSIONID`，并更新 cookies.json 文件。
    """
    try:
        import browser_cookie3
        logging.info("从浏览器获取 Cookie...")
        cookies = browser_cookie3.chrome()
        filtered_cookies = [
            {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
            for c in cookies if c.name in ["atlassian.xsrf.token", "JSESSIONID"]
        ]

        if not any(cookie["name"] == "atlassian.xsrf.token" for cookie in filtered_cookies) or \
           not any(cookie["name"] == "JSESSIONID" for cookie in filtered_cookies):
            logging.error("未找到 atlassian.xsrf.token 或 JSESSIONID。请确保您已在浏览器中登录目标网站。")
            return None

        with open(COOKIE_FILE_PATH, "w", encoding="utf-8") as file:
            json.dump(filtered_cookies, file, indent=4)

        logging.info(f"Cookie 已更新到 {COOKIE_FILE_PATH}")
        return {cookie["name"]: cookie["value"] for cookie in filtered_cookies}
    except Exception as e:
        logging.error(f"从浏览器获取 Cookie 失败: {e}")
        raise


def handle_cookie_expiry(response):
    """
    处理 Cookie 失效的情况。如果检测到失效则重新获取。
    """
    if response.status_code == 401:  # 假设 401 表示 Cookie 失效
        logging.warning("Cookie 失效，重新获取...")
        cookies = get_cookies_from_browser()
        if cookies is None:
            raise Exception("请登录目标网站后重试。")
        return cookies
    return get_cookies_from_browser()

def get_atl_token_and_cookies(cookie_info,cookie_file_path):
    """
    从 cookies.json 文件中提取 atl_token 和 Cookies
    """

    if cookie_info:
        if isinstance(cookie_info, str):
            cookies_list = json.loads(cookie_info)
        cookies_dict = {}
        for cookie in cookies_list:
            if cookie["name"] in ["atlassian.xsrf.token", "JSESSIONID"]:
                cookies_dict[cookie["name"]] = cookie["value"]
            if cookie["name"] == "atlassian.xsrf.token":
                atl_token = cookie["value"]
        if not atl_token:
            raise Exception("atl_token not found in cookies.json")
        return atl_token, cookies_dict

    try:
        with open(cookie_file_path, "r", encoding="utf-8") as file:
            cookies = json.load(file)
            atl_token = None
            cookies_dict = {}
            for cookie in cookies:
                if cookie["name"] in ["atlassian.xsrf.token", "JSESSIONID"]:
                    cookies_dict[cookie["name"]] = cookie["value"]
                if cookie["name"] == "atlassian.xsrf.token":
                    atl_token = cookie["value"]

            if not atl_token:
                raise Exception("atl_token not found in cookies.json")
            return atl_token, cookies_dict
    except Exception as e:
        raise Exception(f"[ERROR] Failed to retrieve atl_token and cookies: {e}")


def format_cookies(cookies_list):
    """
    将 cookies 列表格式化为一个 'key=value' 格式的字符串。
    :param cookies_list: 输入的 Cookie 列表，应该是字典格式
    :return: 格式化后的 Cookie 字符串
    """
    # 检查 cookies_list 中的每个元素是否是字典
    if isinstance(cookies_list, str):
        cookies_list = json.loads(cookies_list)  # 如果是字符串，将其解析为字典

    # 确保每个 cookie 是字典格式并且包含 "name" 和 "value"
    cookie_str = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_list if
                            isinstance(cookie, dict) and 'name' in cookie and 'value' in cookie])
    logging.info(f"Formatted cookie string: {cookie_str}")
    return cookie_str


def load_cookies():
    """
    加载 cookies.json 文件，如果文件不存在则尝试从浏览器重新获取。
    :return: 已加载的 Cookie 字典
    """
    try:
        with open(COOKIE_FILE_PATH, "r", encoding="utf-8") as file:
            cookies_data = json.load(file)
            return format_cookies(cookies_data)
    except Exception as e:
        logging.error(f"加载 Cookie 文件失败: {e}")
        raise
