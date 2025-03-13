import sys
import os
import json
import yaml
from datetime import datetime
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from src.scrapers.prtimes_scraper import PRTimesScraper

def json_serializer(obj):
    """datetime objectをJSON形式に変換するためのシリアライザ"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def main():
    # テスト用のURL
    conf_path = os.path.join(os.path.dirname(__file__), "../configs/companies.yaml")
    with open(conf_path, "r", encoding="utf-8") as f:
        config =yaml.safe_load(f)

    for company_info in config.get("companies", []):
        url = company_info.get("prtimes").get("url")

        test_url = url
        
        print(f"Scraping URL: {test_url}")
        print("Initializing scraper...")
        
        scraper = PRTimesScraper()
        
        print("Starting scraping...")
        articles = scraper.get_news(test_url)
        
        print(f"\nFound {len(articles)} articles")
        print("\nFirst 3 articles:")
        
        # 最初の3記事を整形して表示
        for i, article in enumerate(articles[:3], 1):
            print(f"\n--- Article {i} ---")
            print(f"Title: {article.get('title')}")
            print(f"URL: {article.get('url')}")
            print(f"Published: {article.get('published_at')}")
            print(f"Company: {article.get('company_name')}")
        
    # 全記事をJSONファイルに保存
    output_file = "scraped_articles.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2, default=json_serializer)
    
    print(f"\nAll articles have been saved to {output_file}")

if __name__ == "__main__":
    main() 