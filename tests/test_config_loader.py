"""config_loader 모듈 테스트"""
import os
from pathlib import Path
from modules.config_loader import ConfigLoader, load_config


def test_basic_config_loading():
    """기본 설정 파일 로드 테스트"""
    config = ConfigLoader("config.yaml")
    
    # 기본 설정 확인
    assert config.get("db.path") is not None
    assert config.get("logging.log_dir") is not None
    assert config.get("crawler.max_concurrent") is not None


def test_profile_loading():
    """프로파일별 설정 테스트"""
    # dev 프로파일
    dev_config = ConfigLoader("config.yaml", profile="dev")
    assert dev_config.get("logging.level") == "DEBUG"
    assert dev_config.get("crawler.max_concurrent") == 3
    
    # prod 프로파일
    prod_config = ConfigLoader("config.yaml", profile="prod")
    assert prod_config.get("logging.level") == "INFO"
    assert prod_config.get("crawler.max_concurrent") == 10


def test_env_override():
    """환경 변수 오버라이드 테스트"""
    # 환경 변수 설정
    os.environ["DB_PATH"] = "test.db"
    os.environ["LOG_LEVEL"] = "ERROR"
    os.environ["CRAWLER_MAX_CONCURRENT"] = "20"
    
    config = ConfigLoader("config.yaml")
    
    # 환경 변수로 오버라이드된 값 확인
    assert config.get("db.path") == "test.db"
    assert config.get("logging.level") == "ERROR"
    assert config.get("crawler.max_concurrent") == 20
    
    # 환경 변수 정리
    del os.environ["DB_PATH"]
    del os.environ["LOG_LEVEL"]
    del os.environ["CRAWLER_MAX_CONCURRENT"]


def test_validation():
    """설정 검증 테스트"""
    config = ConfigLoader("config.yaml")
    errors = config.validate()
    
    # 기본 설정은 검증 통과해야 함
    assert len(errors) == 0 or all("required" not in e.lower() for e in errors)


def test_get_with_default():
    """기본값 반환 테스트"""
    config = ConfigLoader("config.yaml")
    
    # 존재하지 않는 키
    assert config.get("nonexistent.key", "default") == "default"
    
    # 존재하는 키
    assert config.get("db.path") is not None


def test_to_dict():
    """딕셔너리 변환 테스트"""
    config = ConfigLoader("config.yaml")
    config_dict = config.to_dict()
    
    assert isinstance(config_dict, dict)
    assert "db" in config_dict
    assert "crawler" in config_dict


if __name__ == "__main__":
    print("config_loader 테스트 실행 중...")
    
    print("\n1. 기본 설정 로드")
    test_basic_config_loading()
    print("✓ 성공")
    
    print("\n2. 프로파일 로드 (dev/prod)")
    test_profile_loading()
    print("✓ 성공")
    
    print("\n3. 환경 변수 오버라이드")
    test_env_override()
    print("✓ 성공")
    
    print("\n4. 설정 검증")
    test_validation()
    print("✓ 성공")
    
    print("\n5. 기본값 반환")
    test_get_with_default()
    print("✓ 성공")
    
    print("\n6. 딕셔너리 변환")
    test_to_dict()
    print("✓ 성공")
    
    print("\n모든 테스트 통과!")
