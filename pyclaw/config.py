import os
from dotenv import load_dotenv

load_dotenv()

QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-turbo")

# QQ Official Bot
QQ_APPID = os.getenv("QQ_APPID", "")
QQ_SECRET = os.getenv("QQ_SECRET", "")
QQ_SANDBOX = os.getenv("QQ_SANDBOX", "false").lower() == "true"

# 心跳间隔（秒），0 表示禁用
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "1800"))
# 管理员 QQ openid，心跳结果通知发送目标
ADMIN_OPENID = os.getenv("ADMIN_OPENID", "")
