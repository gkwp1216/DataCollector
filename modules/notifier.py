"""
알림 및 모니터링 모듈
- 이메일, Slack, Discord 알림
- 수집 완료/실패 알림
- 메트릭 수집 및 통계
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, List, Any
from datetime import datetime
import aiohttp
import json

logger = logging.getLogger(__name__)


class Notifier:
    """알림 핸들러"""
    
    def __init__(
        self,
        email_config: Optional[Dict[str, Any]] = None,
        slack_config: Optional[Dict[str, str]] = None,
        discord_config: Optional[Dict[str, str]] = None,
        enabled: bool = True
    ):
        """
        Args:
            email_config: 이메일 설정 {"smtp_server", "smtp_port", "username", "password", "from", "to"}
            slack_config: Slack 설정 {"webhook_url"}
            discord_config: Discord 설정 {"webhook_url"}
            enabled: 알림 활성화 여부
        """
        self.email_config = email_config or {}
        self.slack_config = slack_config or {}
        self.discord_config = discord_config or {}
        self.enabled = enabled
        
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self):
        """HTTP 세션 초기화"""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
    
    async def close(self):
        """세션 종료"""
        if self._session is not None:
            await self._session.close()
            self._session = None
    
    def send_email(
        self,
        subject: str,
        body: str,
        html: bool = False
    ) -> bool:
        """
        이메일 알림 전송
        
        Args:
            subject: 제목
            body: 본문
            html: HTML 형식 여부
        
        Returns:
            성공 여부
        """
        if not self.enabled or not self.email_config:
            return False
        
        try:
            # 필수 설정 확인
            required_keys = ["smtp_server", "smtp_port", "username", "password", "from", "to"]
            if not all(key in self.email_config for key in required_keys):
                logger.warning("이메일 설정이 불완전합니다")
                return False
            
            # 메시지 생성
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_config['from']
            msg['To'] = self.email_config['to']
            
            # 본문 추가
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # 이메일 전송
            with smtplib.SMTP(
                self.email_config['smtp_server'],
                self.email_config['smtp_port']
            ) as server:
                server.starttls()
                server.login(
                    self.email_config['username'],
                    self.email_config['password']
                )
                server.send_message(msg)
            
            logger.info("이메일 알림 전송 성공: %s", subject)
            return True
            
        except Exception as e:
            logger.error("이메일 전송 실패: %s", str(e), exc_info=True)
            return False
    
    async def send_slack(
        self,
        text: str,
        attachments: Optional[List[Dict]] = None,
        blocks: Optional[List[Dict]] = None
    ) -> bool:
        """
        Slack 알림 전송
        
        Args:
            text: 메시지 텍스트
            attachments: Slack attachments
            blocks: Slack blocks
        
        Returns:
            성공 여부
        """
        if not self.enabled or not self.slack_config.get('webhook_url'):
            return False
        
        try:
            await self._ensure_session()
            
            payload = {"text": text}
            
            if attachments:
                payload["attachments"] = attachments
            
            if blocks:
                payload["blocks"] = blocks
            
            async with self._session.post(
                self.slack_config['webhook_url'],
                json=payload
            ) as resp:
                if resp.status == 200:
                    logger.info("Slack 알림 전송 성공")
                    return True
                else:
                    logger.warning("Slack 알림 전송 실패: %d", resp.status)
                    return False
        
        except Exception as e:
            logger.error("Slack 전송 실패: %s", str(e), exc_info=True)
            return False
    
    async def send_discord(
        self,
        content: str,
        embeds: Optional[List[Dict]] = None
    ) -> bool:
        """
        Discord 알림 전송
        
        Args:
            content: 메시지 내용
            embeds: Discord embeds
        
        Returns:
            성공 여부
        """
        if not self.enabled or not self.discord_config.get('webhook_url'):
            return False
        
        try:
            await self._ensure_session()
            
            payload = {"content": content}
            
            if embeds:
                payload["embeds"] = embeds
            
            async with self._session.post(
                self.discord_config['webhook_url'],
                json=payload
            ) as resp:
                if resp.status in [200, 204]:
                    logger.info("Discord 알림 전송 성공")
                    return True
                else:
                    logger.warning("Discord 알림 전송 실패: %d", resp.status)
                    return False
        
        except Exception as e:
            logger.error("Discord 전송 실패: %s", str(e), exc_info=True)
            return False
    
    async def notify_collection_complete(
        self,
        total: int,
        success: int,
        failed: int,
        skipped: int,
        duration: float
    ):
        """
        수집 완료 알림
        
        Args:
            total: 전체 수
            success: 성공 수
            failed: 실패 수
            skipped: 건너뛴 수
            duration: 소요 시간 (초)
        """
        if not self.enabled:
            return
        
        success_rate = (success / total * 100) if total > 0 else 0
        
        # 이메일 알림
        if self.email_config:
            subject = f"[Data Collector] 수집 완료 - 성공률 {success_rate:.1f}%"
            body = f"""
데이터 수집이 완료되었습니다.

총 항목: {total}개
성공: {success}개
실패: {failed}개
중복 건너뜀: {skipped}개
성공률: {success_rate:.1f}%
소요 시간: {duration:.1f}초

완료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            self.send_email(subject, body.strip())
        
        # Slack 알림
        if self.slack_config.get('webhook_url'):
            color = "good" if success_rate >= 90 else "warning" if success_rate >= 70 else "danger"
            
            await self.send_slack(
                text=f"데이터 수집 완료 - 성공률 {success_rate:.1f}%",
                attachments=[{
                    "color": color,
                    "fields": [
                        {"title": "총 항목", "value": str(total), "short": True},
                        {"title": "성공", "value": str(success), "short": True},
                        {"title": "실패", "value": str(failed), "short": True},
                        {"title": "중복", "value": str(skipped), "short": True},
                        {"title": "성공률", "value": f"{success_rate:.1f}%", "short": True},
                        {"title": "소요 시간", "value": f"{duration:.1f}초", "short": True}
                    ],
                    "footer": "Data Collector",
                    "ts": int(datetime.now().timestamp())
                }]
            )
        
        # Discord 알림
        if self.discord_config.get('webhook_url'):
            color_map = {"good": 0x36a64f, "warning": 0xff9900, "danger": 0xff0000}
            color = color_map["good"] if success_rate >= 90 else color_map["warning"] if success_rate >= 70 else color_map["danger"]
            
            await self.send_discord(
                content=f"**데이터 수집 완료** - 성공률 {success_rate:.1f}%",
                embeds=[{
                    "color": color,
                    "fields": [
                        {"name": "총 항목", "value": str(total), "inline": True},
                        {"name": "성공", "value": str(success), "inline": True},
                        {"name": "실패", "value": str(failed), "inline": True},
                        {"name": "중복", "value": str(skipped), "inline": True},
                        {"name": "성공률", "value": f"{success_rate:.1f}%", "inline": True},
                        {"name": "소요 시간", "value": f"{duration:.1f}초", "inline": True}
                    ],
                    "footer": {"text": "Data Collector"},
                    "timestamp": datetime.now().isoformat()
                }]
            )
    
    async def notify_error(self, error_message: str, details: Optional[str] = None):
        """
        에러 알림
        
        Args:
            error_message: 에러 메시지
            details: 상세 정보
        """
        if not self.enabled:
            return
        
        # 이메일 알림
        if self.email_config:
            subject = "[Data Collector] 에러 발생"
            body = f"""
에러가 발생했습니다:

{error_message}

{f'상세 정보:\n{details}' if details else ''}

발생 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            self.send_email(subject, body.strip())
        
        # Slack 알림
        if self.slack_config.get('webhook_url'):
            await self.send_slack(
                text=":warning: 에러 발생",
                attachments=[{
                    "color": "danger",
                    "title": error_message,
                    "text": details,
                    "footer": "Data Collector",
                    "ts": int(datetime.now().timestamp())
                }]
            )
        
        # Discord 알림
        if self.discord_config.get('webhook_url'):
            await self.send_discord(
                content=f"⚠️ **에러 발생**\n{error_message}",
                embeds=[{
                    "color": 0xff0000,
                    "description": details or "상세 정보 없음",
                    "footer": {"text": "Data Collector"},
                    "timestamp": datetime.now().isoformat()
                }] if details else None
            )


class MetricsCollector:
    """메트릭 수집기"""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "skipped_requests": 0,
            "total_duration": 0.0,
            "errors": [],
            "start_time": None,
            "end_time": None
        }
    
    def start(self):
        """수집 시작"""
        self.metrics["start_time"] = datetime.now()
    
    def end(self):
        """수집 종료"""
        self.metrics["end_time"] = datetime.now()
        if self.metrics["start_time"]:
            duration = (self.metrics["end_time"] - self.metrics["start_time"]).total_seconds()
            self.metrics["total_duration"] = duration
    
    def record_success(self):
        """성공 기록"""
        self.metrics["total_requests"] += 1
        self.metrics["successful_requests"] += 1
    
    def record_failure(self, error: str):
        """실패 기록"""
        self.metrics["total_requests"] += 1
        self.metrics["failed_requests"] += 1
        self.metrics["errors"].append({
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
    
    def record_skip(self):
        """건너뜀 기록"""
        self.metrics["total_requests"] += 1
        self.metrics["skipped_requests"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """메트릭 반환"""
        metrics = self.metrics.copy()
        
        # 성공률 계산
        if metrics["total_requests"] > 0:
            metrics["success_rate"] = (
                metrics["successful_requests"] / metrics["total_requests"] * 100
            )
        else:
            metrics["success_rate"] = 0.0
        
        # 평균 처리 시간
        if metrics["total_requests"] > 0 and metrics["total_duration"] > 0:
            metrics["avg_duration"] = metrics["total_duration"] / metrics["total_requests"]
        else:
            metrics["avg_duration"] = 0.0
        
        return metrics
    
    def get_summary(self) -> str:
        """메트릭 요약 문자열"""
        metrics = self.get_metrics()
        
        summary = f"""
=== 수집 통계 ===
총 요청: {metrics['total_requests']}
성공: {metrics['successful_requests']}
실패: {metrics['failed_requests']}
건너뜀: {metrics['skipped_requests']}
성공률: {metrics['success_rate']:.1f}%
총 소요 시간: {metrics['total_duration']:.1f}초
평균 처리 시간: {metrics['avg_duration']:.2f}초
        """
        
        return summary.strip()
    
    def reset(self):
        """메트릭 초기화"""
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "skipped_requests": 0,
            "total_duration": 0.0,
            "errors": [],
            "start_time": None,
            "end_time": None
        }
