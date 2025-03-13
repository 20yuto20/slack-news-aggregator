import pytest
import os
import yaml
from src.scrapers.prtimes_scraper import PRTimesScraper

@pytest.mark.integration
def test_prtimes_scraper_integration():
    """
    companies.yamlに記述されている各企業のPRTimes URLを実際にスクレイピングして、
    タイトルや公開日時など欲しい値を取得できているかを確認するテスト。
    """
    config_path = os.path.join(os.path.dirname(__file__), '../src/configs/companies.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    scraper = PRTimesScraper()
    for company in config.get('companies', []):
        prtimes_settings = company.get('prtimes')
        print(f"prtimes_settimgs: {prtimes_settings}")
        if not prtimes_settings:
            continue

        if prtimes_settings.get('enabled', False) is False:
            continue

        url = prtimes_settings.get('url')
        print(f"url: {url}")
        if not url:
            continue

        # 実際にPRTIMESをスクレイピングして記事取得
        articles = scraper.get_news(url)

        # 取得した記事の最低限の検証
        # ※ PR TIMES 側でまだ記事がない場合は0件の可能性もあるので要注意
        assert len(articles) > 0, f"Expected to find at least one article for {company['name']} at {url}"

        for article in articles:
            assert 'title' in article, "Each article must have a 'title'"
            assert 'url' in article, "Each article must have a 'url'"
            assert 'published_at' in article, "Each article must have a 'published_at'"
            assert 'source' in article, "Each article must have a 'source'"
