"""
Notifier 모듈 테스트
이메일, Slack, Discord 알림과 메트릭 수집 기능을 검증합니다.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import aiohttp
from modules.notifier import Notifier, MetricsCollector


# ========== MetricsCollector 테스트 ==========

def test_metrics_collector_initialization():
    """MetricsCollector 초기화 테스트"""
    metrics = MetricsCollector()
    
    assert metrics.metrics["total_requests"] == 0
    assert metrics.metrics["successful_requests"] == 0
    assert metrics.metrics["failed_requests"] == 0
    assert metrics.metrics["skipped_requests"] == 0
    assert metrics.metrics["start_time"] is None
    assert metrics.metrics["end_time"] is None
    assert len(metrics.metrics["errors"]) == 0


def test_metrics_record_success():
    """성공 요청 기록 테스트"""
    metrics = MetricsCollector()
    
    metrics.record_success()
    metrics.record_success()
    metrics.record_success()
    
    assert metrics.metrics["total_requests"] == 3
    assert metrics.metrics["successful_requests"] == 3
    assert metrics.metrics["failed_requests"] == 0
    assert metrics.metrics["skipped_requests"] == 0


def test_metrics_record_failure():
    """실패 요청 기록 테스트"""
    metrics = MetricsCollector()
    
    metrics.record_failure("Connection timeout")
    metrics.record_failure("404 Not Found")
    
    assert metrics.metrics["total_requests"] == 2
    assert metrics.metrics["successful_requests"] == 0
    assert metrics.metrics["failed_requests"] == 2
    assert metrics.metrics["skipped_requests"] == 0
    assert len(metrics.metrics["errors"]) == 2


def test_metrics_record_skip():
    """스킵 요청 기록 테스트"""
    metrics = MetricsCollector()
    
    metrics.record_skip()
    metrics.record_skip()
    
    assert metrics.metrics["total_requests"] == 2
    assert metrics.metrics["successful_requests"] == 0
    assert metrics.metrics["failed_requests"] == 0
    assert metrics.metrics["skipped_requests"] == 2


def test_metrics_success_rate_calculation():
    """성공률 계산 테스트"""
    metrics = MetricsCollector()
    
    # 성공 7개, 실패 3개 = 70% 성공률
    for _ in range(7):
        metrics.record_success()
    for _ in range(3):
        metrics.record_failure("Error")
    
    result = metrics.get_metrics()
    
    assert result["total_requests"] == 10
    assert result["successful_requests"] == 7
    assert result["failed_requests"] == 3
    assert result["success_rate"] == 70.0


def test_metrics_timing():
    """시작/종료 시간 기록 테스트"""
    metrics = MetricsCollector()
    
    metrics.start()
    assert metrics.metrics["start_time"] is not None
    
    start_time_snapshot = metrics.metrics["start_time"]
    
    metrics.end()
    assert metrics.metrics["end_time"] is not None
    assert metrics.metrics["end_time"] >= start_time_snapshot


def test_metrics_get_summary():
    """요약 문자열 생성 테스트"""
    metrics = MetricsCollector()
    
    metrics.record_success()
    metrics.record_success()
    metrics.record_failure("Error 1")
    metrics.record_skip()
    
    summary = metrics.get_summary()
    
    assert "총 요청: 4" in summary
    assert "성공: 2" in summary
    assert "실패: 1" in summary
    assert "건너뜀: 1" in summary
    assert "성공률: 50.0%" in summary


# ========== Notifier 테스트 ==========

def test_notifier_initialization_disabled():
    """Notifier 비활성화 초기화 테스트"""
    notifier = Notifier(enabled=False)
    
    assert notifier.enabled is False
    assert notifier.email_config == {}
    assert notifier.slack_config == {}
    assert notifier.discord_config == {}


def test_notifier_initialization_with_email():
    """Notifier 이메일 설정 초기화 테스트"""
    email_config = {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "test@example.com",
        "password": "password",
        "from": "test@example.com",
        "to": "recipient@example.com"
    }
    
    notifier = Notifier(email_config=email_config, enabled=True)
    
    assert notifier.enabled is True
    assert notifier.email_config == email_config


@patch('smtplib.SMTP')
def test_send_email_success(mock_smtp):
    """이메일 전송 성공 테스트"""
    email_config = {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "test@example.com",
        "password": "password",
        "from": "test@example.com",
        "to": "recipient@example.com"
    }
    
    # Mock SMTP 객체
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server
    
    notifier = Notifier(email_config=email_config, enabled=True)
    
    # 이메일 전송
    notifier.send_email("Test Subject", "Test Body")
    
    # SMTP 호출 검증
    mock_smtp.assert_called_once_with(email_config["smtp_server"], email_config["smtp_port"])
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with(email_config["username"], email_config["password"])
    mock_server.send_message.assert_called_once()


@patch('smtplib.SMTP')
def test_send_email_disabled(mock_smtp):
    """비활성화 시 이메일 전송하지 않음 테스트"""
    email_config = {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "test@example.com",
        "password": "password",
        "from": "test@example.com",
        "to": "recipient@example.com"
    }
    
    notifier = Notifier(email_config=email_config, enabled=False)
    
    # 이메일 전송 시도
    notifier.send_email("Test Subject", "Test Body")
    
    # SMTP가 호출되지 않아야 함
    mock_smtp.assert_not_called()


@pytest.mark.asyncio
async def test_send_slack_success():
    """Slack 알림 전송 성공 테스트"""
    slack_config = {
        "webhook_url": "https://hooks.slack.com/services/TEST/WEBHOOK/URL"
    }
    
    notifier = Notifier(slack_config=slack_config, enabled=True)
    await notifier._ensure_session()
    
    # Mock aiohttp session
    with patch.object(notifier._session, 'post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        await notifier.send_slack("Test message")
        
        # POST 호출 검증
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == slack_config["webhook_url"]
    
    await notifier.close()


@pytest.mark.asyncio
async def test_send_discord_success():
    """Discord 알림 전송 성공 테스트"""
    discord_config = {
        "webhook_url": "https://discord.com/api/webhooks/TEST/WEBHOOK"
    }
    
    notifier = Notifier(discord_config=discord_config, enabled=True)
    await notifier._ensure_session()
    
    # Mock aiohttp session
    with patch.object(notifier._session, 'post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 204
        mock_post.return_value.__aenter__.return_value = mock_response
        
        await notifier.send_discord("Test message")
        
        # POST 호출 검증
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == discord_config["webhook_url"]
    
    await notifier.close()


@pytest.mark.asyncio
async def test_notify_collection_complete():
    """수집 완료 알림 테스트"""
    slack_config = {
        "webhook_url": "https://hooks.slack.com/services/TEST/WEBHOOK/URL"
    }
    
    notifier = Notifier(slack_config=slack_config, enabled=True)
    
    # Mock send_slack
    with patch.object(notifier, 'send_slack', new_callable=AsyncMock) as mock_send:
        await notifier.notify_collection_complete(
            total=100,
            success=80,
            failed=15,
            skipped=5,
            duration=120.5
        )
        
        # send_slack이 호출되었는지 검증
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        
        # text 인자 확인
        assert "text" in call_args[1]
        message = call_args[1]["text"]
        assert "수집 완료" in message
        assert "80.0%" in message  # success_rate
        
        # attachments 확인
        assert "attachments" in call_args[1]
        attachments = call_args[1]["attachments"]
        assert len(attachments) > 0


@pytest.mark.asyncio
async def test_notify_error():
    """에러 알림 테스트"""
    discord_config = {
        "webhook_url": "https://discord.com/api/webhooks/TEST/WEBHOOK"
    }
    
    notifier = Notifier(discord_config=discord_config, enabled=True)
    
    # Mock send_discord
    with patch.object(notifier, 'send_discord', new_callable=AsyncMock) as mock_send:
        await notifier.notify_error(
            error_message="Database connection failed",
            details="Connection timeout after 30s"
        )
        
        # send_discord이 호출되었는지 검증
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        
        # content 인자 확인
        assert "content" in call_args[1]
        message = call_args[1]["content"]
        assert "에러 발생" in message
        assert "Database connection failed" in message
        
        # embeds 확인 (details는 embed description에 있음)
        assert "embeds" in call_args[1]
        embeds = call_args[1]["embeds"]
        assert len(embeds) > 0
        assert embeds[0]["description"] == "Connection timeout after 30s"


@pytest.mark.asyncio
async def test_notifier_close():
    """Notifier 세션 종료 테스트"""
    notifier = Notifier(enabled=True)
    await notifier._ensure_session()
    
    # Mock session.close()
    with patch.object(notifier._session, 'close', new_callable=AsyncMock) as mock_close:
        await notifier.close()
        
        # close가 호출되었는지 검증
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_send_slack_http_error():
    """Slack 전송 실패 처리 테스트"""
    slack_config = {
        "webhook_url": "https://hooks.slack.com/services/TEST/WEBHOOK/URL"
    }
    
    notifier = Notifier(slack_config=slack_config, enabled=True)
    await notifier._ensure_session()
    
    # Mock aiohttp session - HTTP 오류 반환
    with patch.object(notifier._session, 'post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # 예외가 발생하지 않고 로그만 남기는지 확인
        await notifier.send_slack("Test message")
        
        # POST 호출은 되어야 함
        mock_post.assert_called_once()
    
    await notifier.close()


@pytest.mark.asyncio
async def test_send_discord_network_error():
    """Discord 전송 네트워크 오류 처리 테스트"""
    discord_config = {
        "webhook_url": "https://discord.com/api/webhooks/TEST/WEBHOOK"
    }
    
    notifier = Notifier(discord_config=discord_config, enabled=True)
    await notifier._ensure_session()
    
    # Mock aiohttp session - 네트워크 오류 발생
    with patch.object(notifier._session, 'post') as mock_post:
        mock_post.side_effect = aiohttp.ClientError("Connection refused")
        
        # 예외가 발생하지 않고 로그만 남기는지 확인
        await notifier.send_discord("Test message")
        
        # POST 호출은 시도되어야 함
        mock_post.assert_called_once()
    
    await notifier.close()
