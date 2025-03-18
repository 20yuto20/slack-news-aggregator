#!/bin/bash
mkdir -p bin/
cd bin/

# Headless Chrome のダウンロード
echo "Downloading Headless Chrome..."
wget -q https://github.com/adieuadieu/serverless-chrome/releases/download/v1.0.0-55/stable-headless-chromium-amazonlinux-2017-03.zip
unzip stable-headless-chromium-amazonlinux-2017-03.zip
rm stable-headless-chromium-amazonlinux-2017-03.zip
chmod +x headless-chromium

# ChromeDriver のダウンロード
echo "Downloading ChromeDriver..."
wget -q https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
rm chromedriver_linux64.zip
chmod +x chromedriver

echo "Done!"