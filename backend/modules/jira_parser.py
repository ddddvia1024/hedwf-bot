from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
import logging
import requests

from backend.config import BASE_JIRA_URL
from backend.modules.ai_deepseek import get_module_from_deepseek
from backend.modules.cookie import format_cookies, load_cookies, handle_cookie_expiry

# 记录日志配置
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

MODULE_OWNERS = {
    "员工信息管理": "menglw",
    "混合云同步": "menglw",
    "入职管理": "liguann",
    "离职管理": "weipsen",
    "部门工作交接": "weipsen",
    "调动管理": "madhui",
    "转正管理": "madhui",
    "其他任职管理": "madhui",
    "需求管理": "lkc",
    "其他": "hedwf",
    "转单办理": "majwr",
    "黑名单": "majwr",
    "报表系统": "majwr",
    "移动端": "yanglih"
# 添加更多模块映射...
}


def fetch_with_browser_cookie(url, cookies=None, session=None):
    """
    使用提供的 Cookie 或默认浏览器 Cookie 访问目标 URL。
    :param url: 目标网址
    :param cookies: 已加载的 Cookie 字典（如果提供）
    :return: 返回请求成功的网页 HTML 内容
    """
    headers = {}
    if cookies:
        cookies_str = format_cookies(cookies)  # 使用格式化后的 Cookie 字符串
        headers["Cookie"] = cookies_str
        headers["User-Agent"]= "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    else:
        # 默认使用浏览器获取 Cookie
        cookies = load_cookies()
        cookies_str = format_cookies(cookies)
        headers["Cookie"] = cookies_str
        headers["User-Agent"]= "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"

    try:

        # 使用传入的session或新建session
        _session = session or requests.Session()
        response = _session.get(url, headers=headers, timeout=30)


        # 如果 Cookie 失效，则重新获取 Cookie 并重试
        if response.status_code == 401:
            logging.warning("Cookie 失效，重新获取...")
            cookies = handle_cookie_expiry(response)
            cookies_str = format_cookies(cookies)
            headers["Cookie"] = cookies_str
            response = requests.get(url, headers=headers, verify=False)

        if response.status_code == 200:
            return response.text
        else:
            raise Exception(f"Failed to fetch URL: {url}, HTTP Status: {response.status_code}")
    except Exception as e:
        logging.error(f"Error fetching URL {url}: {e}")
        raise


def assign_assignee(description):
    """ 返回包含分析结果的完整对象 """
    ai_result = get_module_from_deepseek(description)

    # 匹配负责人逻辑
    for module_name in MODULE_OWNERS:
        if module_name in ai_result['module']:
            return {
                "assignee": MODULE_OWNERS[module_name],
                "module": ai_result['module'],
                "reasoning": ai_result['reasoning']
            }

    # 默认情况
    return {
        "assignee": "hedwf",
        "module": ai_result['module'],
        "reasoning": ai_result['reasoning']
    }


def original_assign_logic(description):
    """
    根据描述内容分配负责人。
    """
    if '员工信息' in description or '个人信息' in description or '合同模块' in description:
        return 'menglw'
    elif '入职' in description or 'offer' in description or '智能复核方案' in description or '候选人' in description or 'OFFER管理中心' in description  or '入职服务中心' in description :
        return 'liguann'
    elif '离职' in description or '部门工作交接' in description or '自定义信息集' in description:
        return 'weipsen'
    elif '其他任职办理' in description or '转正' in description or '调动' in description:
        return 'madhui'
    elif '报表' in description or '多语' in description or '业务流' in description or '转单办理' in description or '黑名单办理' in description or '交接方案' in description:
        return 'majwr'
    elif '移动端' in description:
        return 'yanglih'
    elif '需求' in description:
        return 'lkc'
    else:
        return 'hedwf'

def parse_and_return_data(issue_url,cookies=None):
    """
    提取 issue-link-key 列表，拼接 URL 并抓取描述、ID (customfield_12208-val) 和分配 Assignee。
    :param issue_url: 包含 issue-list 的页面 URL
    :param cookies: 可选，提供的 cookie 字典
    :return: 解析后的数据列表
    """
    try:
        logging.info(f"开始解析 URL: {issue_url}")

        # 获取 issue-list 页面内容
        html_content = fetch_with_browser_cookie(issue_url, cookies)
        soup = BeautifulSoup(html_content, "html.parser")

        # 提取 issue-link-key
        issue_list = soup.find(class_="issue-list")
        if issue_list:
            issue_keys = [item.text.strip() for item in issue_list.find_all(class_="issue-link-key")]
        else:
            # 如果没有 issue-list，则查找 issuetable 中的 data-issuekey
            issue_table = soup.find("table", id="issuetable")
            if not issue_table:
                raise Exception("No issue-list or issuetable found on the page.")
            issue_keys = [row["data-issuekey"] for row in issue_table.find_all("tr", {"data-issuekey": True})]

        logging.info(f"发现 {len(issue_keys)} 个 issue keys.")


        # 遍历 issue-keys 并抓取描述和 ID
        result_data = []
        # 创建带缓存的Session提升请求效率
        session = requests.Session()
        session.verify = False

        # 封装单任务处理函数
        def process_issue(key):
            try:
                issue_page_url = f"{BASE_JIRA_URL}/{key}"
                logging.info(f"Fetching details for: {issue_page_url}")

                # 使用共享Session发起请求
                issue_html = fetch_with_browser_cookie(issue_page_url, cookies, session=session)
                issue_soup = BeautifulSoup(issue_html, "html.parser")

                # 提取描述和ID（保持原有逻辑）
                description_element = issue_soup.find(class_="je_rdata je_pr_required")
                description = description_element.text.strip() if description_element else "No description found"

                customfield_element = issue_soup.find(id="customfield_12208-val")
                issue_id = customfield_element.text.strip() if customfield_element else "No ID found"

                # 异步分配负责人（可并行处理）
                assign_result = assign_assignee(description)

                return {
                    "url": issue_page_url,
                    "description": description,
                    "id": issue_id,
                    "assignee": assign_result["assignee"],
                    "module": assign_result["module"],
                    "reasoning": assign_result["reasoning"]
                }
            except Exception as e:
                logging.error(f"处理问题 {key} 失败: {e}")
                return None

        # 使用线程池并发处理（建议并发数5-10）
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(process_issue, key): key for key in issue_keys}

            for future in as_completed(futures):
                result = future.result()
                if result:
                    result_data.append(result)

        logging.info("解析完成")
        return result_data
    except Exception as e:
        logging.error(f"解析失败: {e}")
        raise