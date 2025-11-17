import pytest
from modules.rss_reader import RSSReader


# 샘플 RSS 피드 XML
SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Sample Feed</title>
        <link>https://example.com</link>
        <description>Test RSS Feed</description>
        <item>
            <title>First Article</title>
            <link>https://example.com/article1</link>
            <description>This is the first article</description>
            <pubDate>Mon, 18 Nov 2025 10:00:00 GMT</pubDate>
            <author>John Doe</author>
        </item>
        <item>
            <title>Second Article</title>
            <link>https://example.com/article2</link>
            <description>This is the second article</description>
            <pubDate>Mon, 18 Nov 2025 11:00:00 GMT</pubDate>
        </item>
    </channel>
</rss>
"""

SAMPLE_ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>Sample Atom Feed</title>
    <link href="https://example.com/feed"/>
    <updated>2025-11-18T12:00:00Z</updated>
    <entry>
        <title>Atom Entry</title>
        <link href="https://example.com/entry1"/>
        <id>entry1</id>
        <updated>2025-11-18T12:00:00Z</updated>
        <summary>Atom entry summary</summary>
    </entry>
</feed>
"""


def test_parse_rss_feed():
    """RSS 피드 파싱 테스트"""
    reader = RSSReader()
    result = reader.parse_feed(SAMPLE_RSS, feed_url="https://example.com/rss")
    
    assert result["title"] == "Sample Feed"
    assert result["feed_url"] == "https://example.com/rss"
    assert len(result["entries"]) == 2
    
    # 첫 번째 항목 확인
    first = result["entries"][0]
    assert first["title"] == "First Article"
    assert first["link"] == "https://example.com/article1"
    assert first["author"] == "John Doe"
    assert "first article" in first["description"]


def test_parse_atom_feed():
    """Atom 피드 파싱 테스트"""
    reader = RSSReader()
    result = reader.parse_feed(SAMPLE_ATOM, feed_url="https://example.com/atom")
    
    assert result["title"] == "Sample Atom Feed"
    assert len(result["entries"]) == 1
    
    entry = result["entries"][0]
    assert entry["title"] == "Atom Entry"
    assert entry["id"] == "entry1"
    assert "Atom entry summary" in entry["summary"]


def test_clean_html():
    """HTML 정제 테스트"""
    reader = RSSReader()
    
    html = "<p>Test <strong>content</strong> with <a href='#'>link</a></p>"
    cleaned = reader._clean_html(html)
    
    assert "<p>" not in cleaned
    assert "<strong>" not in cleaned
    assert "Test content with link" == cleaned


def test_parse_date():
    """날짜 파싱 테스트"""
    reader = RSSReader()
    
    # time.struct_time 형식
    import time
    date_tuple = time.strptime("2025-11-18 10:00:00", "%Y-%m-%d %H:%M:%S")
    result = reader._parse_date(date_tuple)
    
    assert result is not None
    assert "2025-11-18" in result
    
    # None 처리
    result_none = reader._parse_date(None)
    assert result_none is None


@pytest.mark.asyncio
async def test_fetch_and_parse_integration():
    """통합 테스트 (실제 피드 없이 파싱만)"""
    reader = RSSReader()
    
    # parse_feed는 동기 함수이므로 직접 호출
    result = reader.parse_feed(SAMPLE_RSS)
    
    assert result is not None
    assert "entries" in result
    assert len(result["entries"]) > 0
    
    await reader.close()


def test_empty_feed():
    """빈 피드 처리"""
    reader = RSSReader()
    empty_rss = """<?xml version="1.0"?>
    <rss version="2.0">
        <channel>
            <title>Empty Feed</title>
        </channel>
    </rss>"""
    
    result = reader.parse_feed(empty_rss)
    assert result["title"] == "Empty Feed"
    assert len(result["entries"]) == 0


def test_malformed_feed():
    """잘못된 형식의 피드 처리"""
    reader = RSSReader()
    malformed = "Not a valid XML or RSS feed"
    
    # feedparser는 에러를 발생시키지 않고 빈 결과 반환
    result = reader.parse_feed(malformed)
    assert result is not None
    assert "entries" in result
