import requests
import logging
from functools import lru_cache

# 在文件顶部添加配置（需要先获取Deepseek API key）
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = "sk-f45ad4cb44ae4a6c838758d832a6d0d2"  # 需要替换为实际API Key
HEADERS = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json"
}



# 添加缓存避免重复请求（可根据需要调整maxsize）
@lru_cache(maxsize=100)
def get_module_from_deepseek(description: str) -> str:
    """
    调用Deepseek API分析问题描述返回模块分类
    """
    try:
        payload = {
            "model": "deepseek-reasoner",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个JIRA问题分类助手，请根据问题描述判断属于哪个模块，只需返回模块名称，不要任何解释。可选模块：员工信息、入职管理、离职管理、调动管理、转正管理、报表系统、黑名单、其他任职管理、混合云同步、转单办理、移动端、需求管理、其他、部门工作交接"
                },
                {
                    "role": "user",
                    "content": f"问题描述：{description}"
                }
            ],
            "temperature": 1
        }

        response = requests.post(DEEPSEEK_API_URL, json=payload, headers=HEADERS, timeout=240)
        logging.info(f"[SUCCESS] Deepseek API调用成功:{response.text}")
        response.raise_for_status()

        # 解析返回结果
        response_data = response.json()
        return {
            "module": response_data['choices'][0]['message']['content'].strip(),
            "reasoning": response_data['choices'][0]['message']['reasoning_content']
        }
    except Exception as e:
        logging.error(f"Deepseek API调用失败: {e}")
        return {"module": "其他", "reasoning": "AI分析失败"}
