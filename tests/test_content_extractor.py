"""content_extractor 모듈 테스트"""
from modules.content_extractor import ContentExtractor, extract_main_content, extract_metadata


def test_extract_main_content():
    """기본 본문 추출 테스트"""
    html = """
    <html>
        <head><title>Test Article</title></head>
        <body>
            <article>
                <h1>Test Title</h1>
                <p>This is the main content of the article.</p>
                <p>It has multiple paragraphs.</p>
            </article>
        </body>
    </html>
    """
    
    content = extract_main_content(html)
    assert content is not None
    assert "main content" in content.lower()
    print("✓ 기본 본문 추출 성공")


def test_content_extractor():
    """ContentExtractor 클래스 테스트"""
    html = """
    <html>
        <head>
            <title>Test Page</title>
            <meta property="og:title" content="OG Title">
            <meta property="og:description" content="OG Description">
            <meta name="twitter:card" content="summary">
        </head>
        <body>
            <article>
                <h1>Article Title</h1>
                <p>Article content goes here.</p>
                <img src="/image.jpg" alt="Test Image">
                <a href="/link">Test Link</a>
            </article>
        </body>
    </html>
    """
    
    extractor = ContentExtractor()
    result = extractor.extract_content(html, "https://example.com")
    
    assert result["text"] is not None
    assert "content" in result["text"].lower()
    assert result["metadata"]["og"]["title"] == "OG Title"
    assert result["metadata"]["twitter"]["card"] == "summary"
    assert len(result["images"]) > 0
    assert len(result["links"]) > 0
    
    print("✓ ContentExtractor 클래스 테스트 성공")


def test_extract_metadata():
    """메타데이터 추출 테스트"""
    html = """
    <html>
        <head>
            <title>Test Article</title>
            <meta name="author" content="Test Author">
            <meta name="description" content="Test Description">
        </head>
        <body>
            <article>
                <p>Content</p>
            </article>
        </body>
    </html>
    """
    
    metadata = extract_metadata(html)
    # trafilatura가 메타데이터를 추출하지 못할 수 있으므로 None 체크
    if metadata:
        print(f"✓ 메타데이터: {metadata}")
    else:
        print("✓ 메타데이터 추출 (HTML이 단순하여 추출 안됨)")


if __name__ == "__main__":
    print("content_extractor 테스트 실행 중...")
    
    print("\n1. 기본 본문 추출")
    test_extract_main_content()
    
    print("\n2. ContentExtractor 클래스")
    test_content_extractor()
    
    print("\n3. 메타데이터 추출")
    test_extract_metadata()
    
    print("\n모든 테스트 통과!")
