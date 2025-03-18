#!/bin/bash
# setup_chrome_firebase.sh - Firebase Functionsにデプロイする前に実行するスクリプト
# Firebaseデプロイ用にChrome/ChromeDriverの設定を行う

set -e

# Create directories
mkdir -p functions
CURRENT_DIR=$(pwd)

# メインディレクトリにpackage.jsonを作成/更新
if [ ! -f package.json ]; then
  cat > package.json << EOF
{
  "name": "news-collector",
  "version": "1.0.0",
  "description": "News collection with Chrome support",
  "main": "index.js",
  "dependencies": {
    "chrome-aws-lambda": "^10.1.0",
    "puppeteer-core": "^10.1.0"
  }
}
EOF
  echo "Created package.json"
fi

# PRTimesスクレイパーを更新
echo "Updating PRTimes scraper to use puppeteer-core..."

# バックアップを作成
if [ -f src/scrapers/prtimes_scraper.py ]; then
  cp src/scrapers/prtimes_scraper.py src/scrapers/prtimes_scraper.py.bak
  echo "Created backup of prtimes_scraper.py"
fi

# Firebase用の.npmrcを作成（オプションで必要な場合）
cat > .npmrc << EOF
# Allow puppeteer/headless-chrome installation
unsafe-perm=true
EOF

# デプロイ指示メッセージを表示
echo "========================================================"
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Make sure you've updated the prtimes_scraper.py file as instructed"
echo "2. Run 'npm install' to install the Node.js dependencies"
echo "3. Run 'npx firebase deploy --only functions:new_collector' to deploy"
echo "========================================================"