FROM python:3.10

WORKDIR /app

# 安装 uv
RUN pip install uv

# 复制项目文件
COPY . /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 安装 Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 用 uv 安装依赖（假设你有 pyproject.toml）
RUN uv pip install --system -r requirements.txt

# 同时运行两个 Python 脚本
CMD ["sh", "-c", "python 启动AI客服main.py & python 超级简历接码服务器main.py && wait"]