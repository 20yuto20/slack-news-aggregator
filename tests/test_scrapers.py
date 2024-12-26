# tests/test_scrapers.py
import pytest
from unittest.mock import patch, MagicMock
from src.scrapers.prtimes_scraper import PRTimesScraper

@pytest.fixture
def mock_scraper():
    return PRTimesScraper()

def test_prtimes_scraper_get_news_empty(mock_scraper):
    # _fetch_page が None を返す場合
    with patch.object(mock_scraper, "_fetch_page", return_value=None):
        articles = mock_scraper.get_news("https://prtimes.jp/main/html/searchrlp/company_id/99999")
        assert articles == []

def test_prtimes_scraper_get_news_ok(mock_scraper):
    # TODO: PRTimesのサイトのHTMLと形式が異なるので修正する
    html_content = """
    <html>
      <body>
        <article class="list-article">
          <h2 class="list-article_title">
            <a href="/release/12345">サンプル記事タイトル</a>
          </h2>
          <time>2024年12月01日 12:34</time>
          <img class="list-article_image" src="https://prtimes.jp/img/sample.png">
          <p class="list-article__summary">これはサマリーです</p>
        </article>
      </body>
    </html>
    """

    with patch.object(mock_scraper, "_fetch_page", return_value=MagicMock()) as mock_page:
        # BeautifulSoup の振る舞いを模擬
        mock_page.return_value.find_all.return_value = [MagicMock()]
        # find_all() が返す article の中身をさらにモック化
        mock_article = MagicMock()
        mock_page.return_value.find_all.return_value = [mock_article]

        # 各 find の戻り値を細かく指定
        title_elem = MagicMock()
        title_elem.find.return_value = MagicMock()
        title_elem.find.return_value.text = "サンプル記事タイトル"
        title_elem.find.return_value.attrs = {'href': '/release/12345'}

        # time要素
        time_elem = MagicMock()
        time_elem.text = "2024年12月01日 12:34"

        # img要素
        img_elem = MagicMock()
        img_elem.attrs = {'src': 'https://prtimes.jp/img/sample.png'}

        # p要素
        content_elem = MagicMock()
        content_elem.text = "これはサマリーです"

        # mock_article.find() の返り値を属性に応じて返す設定
        def mock_find(tag, class_=None):
            if tag == 'h2' and class_ == 'list-article_title':
                return title_elem
            elif tag == 'time':
                return time_elem
            elif tag == 'img' and class_ == 'list-article_image':
                return img_elem
            elif tag == 'p' and class_ == 'list-article__summary':
                return content_elem
            return None

        mock_article.find.side_effect = mock_find

        articles = mock_scraper.get_news("https://prtimes.jp/any_url")
        assert len(articles) == 1
        assert articles[0]['title'] == "サンプル記事タイトル"
        assert "2024-12-01" in articles[0]['published_at'].isoformat()
        assert articles[0]['content'] == "これはサマリーです"
