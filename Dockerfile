FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖（Pillow 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 微信云托管通过 PORT 环境变量注入端口
EXPOSE 80

# 使用 shell form 以便读取环境变量
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-80}"]
