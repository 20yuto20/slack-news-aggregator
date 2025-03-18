import sys
import os
import json
import yaml
from datetime import datetime
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_scraper")

# Add project root to path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

# Import the updated scraper
from src.scrapers.prtimes_scraper import PRTimesScraper

def json_serializer(obj):
    """datetime objectをJSON形式に変換するためのシリアライザ"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def main():
    # Load configuration
    conf_path = os.path.join(os.path.dirname(__file__), "../configs/companies.yaml")
    with open(conf_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    all_articles = []
    
    for company_info in config.get("companies", []):
        prtimes_settings = company_info.get("prtimes")
        if not prtimes_settings or not prtimes_settings.get("enabled", True):
            continue

        url = prtimes_settings.get("url")
        if not url:
            continue
        
        company_name = company_info.get("name", "Unknown")
        print(f"\n{'='*80}")
        print(f"Scraping company: {company_name}")
        print(f"URL: {url}")
        print(f"{'='*80}")
        
        # Initialize scraper with verbose logging
        scraper = PRTimesScraper()
        
        # Run scraping
        print("Starting scraping...")
        articles = scraper.get_news(url)
        
        # Print results
        print(f"\nFound {len(articles)} articles for {company_name}")
        if articles:
            print("\nFirst 5 articles:")
            for i, article in enumerate(articles[:5], 1):
                print(f"\n--- Article {i} ---")
                print(f"Title: {article.get('title')}")
                print(f"URL: {article.get('url')}")
                print(f"Published: {article.get('published_at')}")
                print(f"Company: {article.get('company_name')}")
                
            all_articles.extend(articles)
        else:
            print("No articles found!")
        
    # Save all articles to JSON file
    output_file = os.path.join(project_root, "scraped_articles.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2, default=json_serializer)
    
    print(f"\nAll articles have been saved to {output_file}")
    
    print(f"\nTotal articles found: {len(all_articles)}")
    if len(all_articles) > 0:
        print("Scraping completed successfully!")
    else:
        print("No articles were found. Check the logs for errors.")

if __name__ == "__main__":
    main()