FROM python:3.13-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码和配置文件
COPY pyclaw/ ./pyclaw/
COPY main.py .
COPY mcp_servers.json .
COPY HEARTBEAT.md .

# 运行时创建必要目录
RUN mkdir -p memory skills

CMD ["python", "main.py"]
