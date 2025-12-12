"""
설정 로더 모듈
- YAML 파일 기반 설정
- 환경 변수 오버라이드 (.env 지원)
- 프로파일별 설정 (dev, prod)
- 설정 검증
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv


class ConfigLoader:
    """설정 파일 로더 with 환경 변수 지원"""
    
    def __init__(self, config_path: str = "config.yaml", profile: Optional[str] = None):
        """
        Args:
            config_path: 설정 파일 경로
            profile: 프로파일 이름 (dev, prod 등). 없으면 config.yaml만 사용
        """
        self.config_path = config_path
        self.profile = profile or os.getenv("APP_PROFILE", "default")
        self.config: Dict[str, Any] = {}
        
        # .env 파일 로드 (환경 변수 우선)
        load_dotenv()
        
        # 설정 로드
        self._load_config()
        self._apply_env_overrides()
        
    def _load_config(self):
        """YAML 설정 파일 로드"""
        # 기본 설정 파일
        if Path(self.config_path).exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
        else:
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {self.config_path}")
        
        # 프로파일별 설정 파일 (선택)
        if self.profile != "default":
            profile_path = self.config_path.replace(".yaml", f".{self.profile}.yaml")
            if Path(profile_path).exists():
                with open(profile_path, "r", encoding="utf-8") as f:
                    profile_config = yaml.safe_load(f) or {}
                    self.config = self._deep_merge(self.config, profile_config)
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """딕셔너리 깊은 병합"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _apply_env_overrides(self):
        """환경 변수로 설정 오버라이드"""
        # Database
        if os.getenv("DB_PATH"):
            self.config.setdefault("db", {})["path"] = os.getenv("DB_PATH")
        
        # Logging
        if os.getenv("LOG_DIR"):
            self.config.setdefault("logging", {})["log_dir"] = os.getenv("LOG_DIR")
        if os.getenv("LOG_LEVEL"):
            self.config.setdefault("logging", {})["level"] = os.getenv("LOG_LEVEL")
        if os.getenv("LOG_MAX_BYTES"):
            self.config.setdefault("logging", {})["max_bytes"] = int(os.getenv("LOG_MAX_BYTES"))
        if os.getenv("LOG_BACKUP_COUNT"):
            self.config.setdefault("logging", {})["backup_count"] = int(os.getenv("LOG_BACKUP_COUNT"))
        
        # Crawler
        crawler_config = self.config.setdefault("crawler", {})
        if os.getenv("CRAWLER_MAX_CONCURRENT"):
            crawler_config["max_concurrent"] = int(os.getenv("CRAWLER_MAX_CONCURRENT"))
        if os.getenv("CRAWLER_TIMEOUT"):
            crawler_config["timeout"] = int(os.getenv("CRAWLER_TIMEOUT"))
        if os.getenv("CRAWLER_MAX_RETRIES"):
            crawler_config["max_retries"] = int(os.getenv("CRAWLER_MAX_RETRIES"))
        if os.getenv("CRAWLER_DELAY"):
            crawler_config["delay_between_requests"] = float(os.getenv("CRAWLER_DELAY"))
        if os.getenv("CRAWLER_USER_AGENT"):
            crawler_config["user_agent"] = os.getenv("CRAWLER_USER_AGENT")
        if os.getenv("CRAWLER_SKIP_DUPLICATES"):
            crawler_config["skip_duplicates"] = os.getenv("CRAWLER_SKIP_DUPLICATES").lower() == "true"
        
        # Scheduler
        scheduler_config = self.config.setdefault("scheduler", {})
        if os.getenv("SCHEDULER_ENABLED"):
            scheduler_config["enabled"] = os.getenv("SCHEDULER_ENABLED").lower() == "true"
        if os.getenv("SCHEDULER_INTERVAL_MINUTES"):
            scheduler_config["interval_minutes"] = int(os.getenv("SCHEDULER_INTERVAL_MINUTES"))
        if os.getenv("SCHEDULER_CRON"):
            scheduler_config["cron"] = os.getenv("SCHEDULER_CRON")
        
        # Targets (comma-separated)
        if os.getenv("TARGETS"):
            targets = [url.strip() for url in os.getenv("TARGETS").split(",") if url.strip()]
            if targets:
                self.config["targets"] = targets
        
        # RSS Feeds (comma-separated)
        if os.getenv("RSS_FEEDS"):
            feeds = [url.strip() for url in os.getenv("RSS_FEEDS").split(",") if url.strip()]
            if feeds:
                self.config["rss_feeds"] = feeds
    
    def get(self, key: str, default: Any = None) -> Any:
        """설정 값 가져오기 (점 표기법 지원)"""
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value if value is not None else default
    
    def validate(self) -> List[str]:
        """설정 검증 (필수 항목 확인)"""
        errors = []
        
        # 필수 항목 검증
        if not self.get("db.path"):
            errors.append("db.path is required")
        
        if not self.get("logging.log_dir"):
            errors.append("logging.log_dir is required")
        
        crawler_max_concurrent = self.get("crawler.max_concurrent")
        if crawler_max_concurrent is not None and (crawler_max_concurrent < 1 or crawler_max_concurrent > 50):
            errors.append("crawler.max_concurrent must be between 1 and 50")
        
        crawler_timeout = self.get("crawler.timeout")
        if crawler_timeout is not None and crawler_timeout < 1:
            errors.append("crawler.timeout must be at least 1 second")
        
        # 타겟 URL 검증
        targets = self.get("targets", [])
        if not isinstance(targets, list):
            errors.append("targets must be a list")
        elif not targets and not self.get("rss_feeds"):
            errors.append("At least one target or RSS feed is required")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """설정을 딕셔너리로 반환"""
        return self.config.copy()
    
    def __repr__(self):
        return f"ConfigLoader(profile={self.profile}, config_path={self.config_path})"


def load_config(config_path: str = "config.yaml", profile: Optional[str] = None) -> ConfigLoader:
    """설정 로더 생성 (편의 함수)"""
    loader = ConfigLoader(config_path, profile)
    
    # 검증
    errors = loader.validate()
    if errors:
        raise ValueError(f"설정 검증 실패:\n" + "\n".join(f"  - {e}" for e in errors))
    
    return loader
