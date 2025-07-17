import os

from flask import Flask, request, jsonify, send_from_directory
import requests
import logging

from flask_cors import CORS

from backend.config import BASE_DIR
from backend.modules.jira_parser import parse_and_return_data
from backend.modules.cookie import get_atl_token_and_cookies, load_cookies, format_cookies

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
COOKIE_FILE_PATH = os.path.join(BASE_DIR, "cookies.json")

app = Flask(__name__)
CORS(app)

@app.route('/')
def serve():
    """
    Serve the React application.
    """
    return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(404)
def not_found(e):
    """
    Handle 404 errors by serving the React application.
    """
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """
    接收前端传递的 JIRA URL 和 Cookie 信息，返回解析结果。
    """
    data = request.json
    jira_url = data.get('jira_url')
    cookie_info = data.get('cookies')

    if not jira_url:
        return jsonify({"error": "JIRA URL is required"}), 400

    cookies = {}
    if cookie_info:
        # 如果前端提供了cookie信息，使用该cookie
        cookies = cookie_info  # 请根据实际情况解析cookie
    else:
        cookies = load_cookies()

    try:
        # 调用解析方法，传递jira_url和cookies
        result_data = parse_and_return_data(jira_url, cookies)

        # 返回分析结果
        return jsonify({"results": result_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/assign', methods=['POST'])
def assign_issues():
    """
    从前端接收数据并为每个 issue 分配 Assignee。
    如果 Assignee 是 wangxbd，则调用额外的接口。
    """
    try:
        data = request.json['data']
        cookies = request.json['cookies']
        if not data:
            return jsonify({"error": "No data provided"}), 400


        atl_token, cookies_dict = get_atl_token_and_cookies(cookies,COOKIE_FILE_PATH)
        if cookies:
            # 如果前端提供了cookie信息，使用该cookie
            cookies = format_cookies(cookies)  # 请根据实际情况解析cookie
        else:
            cookies = load_cookies()
        headers = {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-ausername": "hedwf",
            "x-requested-with": "XMLHttpRequest",
            "x-sitemesh-off": "true",
            "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Cookie": cookies,
        }

        for item in data:
            issue_id = item.get("id")
            assignee = item.get("assignee")
            if not issue_id or not assignee:
                continue

            # 调用分配 API
            url = "https://gfjira.yyrd.com/secure/AssignIssue.jspa"
            assign_body = f"id={issue_id}&assignee={assignee}&atl_token={atl_token}&inline=true"
            assign_response = requests.post(url, headers=headers, data=assign_body, verify=False)

            if assign_response.status_code == 200:
                print(f"[SUCCESS] Issue {issue_id} assigned to {assignee}")
            else:
                print(f"[ERROR] Failed to assign issue {issue_id}. Response: {assign_response.text}")

            # 如果 Assignee 是 wangxbd，则调用额外的接口
            if assignee == "menglw":
                additional_url = "https://gfjira.yyrd.com/secure/AjaxIssueAction.jspa?decorator=none"
                additional_body = f"customfield_10123=24501&customfield_10123%3A1=24505&issueId={issue_id}&atl_token={atl_token}&singleFieldEdit=true&fieldsToForcePresent=customfield_10123"
                additional_response = requests.post(additional_url, headers=headers, data=additional_body, verify=False)

                if additional_response.status_code == 200:
                    print(f"[SUCCESS] Additional API called for issue {issue_id}")
                else:
                    print(f"[ERROR] Failed to call additional API for issue {issue_id}. Response: {additional_response.text}")

        return jsonify({"message": "Issues processed successfully"}), 200
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/add-label', methods=['POST'])
def add_label():
    """
    为指定issue添加标签
    请求参数格式：
    {
        "issueId": "7098494",
        "labels": "重点问题分析",
        "cookieInput": "JSESSIONID=...; atlassian.xsrf.token=..."
    }
    """
    try:
        data = request.json
        issue_id = data.get("issueId")
        labels = "重点问题分析"
        cookie_info = data.get("cookieInput", [])

        if not all([issue_id, labels]):
            return jsonify({"error": "Missing required parameters"}), 400

        # 获取安全令牌
        atl_token, cookies_dict = get_atl_token_and_cookies(cookie_info, COOKIE_FILE_PATH)

        # 准备请求参数
        url = "https://gfjira.yyrd.com/secure/AjaxIssueAction.jspa"
        params = {"decorator": "none"}
        headers = {
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Cookie": format_cookies(cookie_info),
            "x-ausername": "hedwf"  # 根据实际需要调整
        }

        # 构建请求体
        payload = {
            "labels": labels,
            "issueId": issue_id,
            "atl_token": atl_token,
            "singleFieldEdit": "true",
            "fieldsToForcePresent": "labels"
        }

        # 发送请求
        response = requests.post(
            url,
            headers=headers,
            params=params,
            data=payload,
            verify=False
        )

        if response.status_code == 200:
            logging.info(f"标签添加成功 - Issue: {issue_id}")
            return jsonify({
                "success": True,
                "message": f"成功为问题 {issue_id} 添加标签: {labels}"
            }), 200
        else:
            logging.error(f"标签添加失败 - {response.text}")
            return jsonify({
                "error": f"JIRA接口返回错误: {response.text}"
            }), 500

    except Exception as e:
        logging.error(f"标签添加异常: {str(e)}")
        return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500



if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)