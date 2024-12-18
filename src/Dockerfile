# Pyhtonの公式イメージをベースに使用
FROM python:3.11-slim

# 作業ディレクトリの設定
WORKDIR /Users/yutokohata/kotonaru_slack_news_app

# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    build essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# 依存関係ファイルをコピー
COPY requirements.txt .

# Python依存関係のインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY . .

# 環境変数の設定
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV ENVIROMENT=production

# チェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit1

# 起動
CMD ["gunicorn", "src.app:app", "--blind", "0.0.0.0:8080", "--workers", "4", "--timeout", "120"]
