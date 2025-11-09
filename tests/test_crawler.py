import pytest

from modules.crawler import AsyncCrawler


def test_parse_html_title_and_snippet():
    html = """
    <html>
      <head><title>테스트 페이지</title></head>
      <body>
        <p>여기는 본문 내용입니다. 이것은 테스트용으로 긴 문자열을 포함합니다.</p>
      </body>
    </html>
    """

    crawler = AsyncCrawler()
    parsed = crawler.parse_html(html, url="https://example.test")
    assert parsed["title"] == "테스트 페이지"
    assert "본문 내용" in parsed["content"]
