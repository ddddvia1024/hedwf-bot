import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cookie 文件路径
COOKIE_FILE_PATH = os.path.join(BASE_DIR, "cookies.json")

# 默认 JIRA URL 和基础 URL
DEFAULT_JIRA_URL = "https://gfjira.yyrd.com/browse/HXRL-103987?filter=83510"
BASE_JIRA_URL = "https://gfjira.yyrd.com/browse"

# 日志配置
LOGGING_FORMAT = "[%(asctime)s] %(levelname)s: %(message)s"
LOGGING_LEVEL = "INFO"

# Flask 应用配置
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000