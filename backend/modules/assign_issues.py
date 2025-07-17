import pandas as pd
import requests
import json
import time
import logging

def assign_issues_from_excel(excel_file_path, cookie_file_path, delay=2):
    """
    从 Excel 文件读取数据并分配任务。
    """
    try:
        logging.info(f"读取 Excel 文件: {excel_file_path}")
        df = pd.read_excel(excel_file_path)

        if "ID" not in df.columns or "assignee" not in df.columns:
            raise Exception("Excel file must contain 'ID' and 'assignee' columns")

        with open(cookie_file_path, "r", encoding="utf-8") as file:
            cookies = json.load(file)

        atl_token = next((c["value"] for c in cookies if c["name"] == "atlassian.xsrf.token"), None)
        if not atl_token:
            raise Exception("atl_token not found in cookies.json")

        cookies_dict = {c["name"]: c["value"] for c in cookies}

        for _, row in df.iterrows():
            issue_id, assignee = row["ID"], row["assignee"]
            url = "https://gfjira.yyrd.com/secure/AssignIssue.jspa"

            headers = {
                "accept": "text/html, */*; q=0.01",
                "content-type": "application/x-www-form-urlencoded",
                "Cookie": "; ".join([f"{k}={v}" for k, v in cookies_dict.items()]),
            }
            body = f"id={issue_id}&assignee={assignee}&atl_token={atl_token}&inline=true"

            logging.info(f"分配任务: ID={issue_id}, Assignee={assignee}")
            response = requests.post(url, headers=headers, data=body, verify=False)
            if response.status_code == 200:
                logging.info(f"[SUCCESS] Issue {issue_id} assigned to {assignee}")
            else:
                logging.error(f"[ERROR] Failed to assign {issue_id}. Response: {response.text}")

            time.sleep(delay)
    except Exception as e:
        logging.error(f"任务分配失败: {e}")
        raise