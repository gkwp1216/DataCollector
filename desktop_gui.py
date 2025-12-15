"""
Desktop GUI for Data Collector using PyQt5
Modern, user-friendly interface for managing the web crawler
"""

import sys
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QTextEdit, QLineEdit, QSpinBox,
    QCheckBox, QTableWidget, QTableWidgetItem, QGroupBox, QGridLayout,
    QProgressBar, QComboBox, QMessageBox, QFileDialog, QStatusBar,
    QSplitter, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor

from modules.crawler import AsyncCrawler
from modules.database import init_db, save_item, get_all_items, get_stats
from modules.config_loader import load_config as load_config_function
from modules.logger import get_logger

logger = get_logger(__name__)


class CrawlerWorker(QThread):
    """Background thread for running crawler"""
    progress_updated = pyqtSignal(int, int)  # current, total
    item_collected = pyqtSignal(str, str, bool)  # url, title, success
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, urls, config):
        super().__init__()
        self.urls = urls
        self.config = config
        self.is_running = True
        
    def run(self):
        """Run crawler in separate thread"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.run_crawler())
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()
    
    async def run_crawler(self):
        """Async crawler execution"""
        db_path = self.config['db']['path']
        await init_db(db_path)
        
        crawler = AsyncCrawler(
            timeout=self.config['crawler'].get('timeout', 10),
            max_retries=self.config['crawler'].get('max_retries', 3),
            use_trafilatura=self.config['crawler'].get('use_trafilatura', False),
            use_playwright=self.config['crawler'].get('use_playwright', False),
            respect_robots=self.config['crawler'].get('respect_robots', True)
        )
        
        total = len(self.urls)
        
        try:
            for idx, url in enumerate(self.urls):
                if not self.is_running:
                    break
                
                try:
                    data = await crawler.fetch_and_parse(url)
                    if data:
                        await save_item(db_path, data)
                        self.item_collected.emit(url, data.get('title', 'No title'), True)
                    else:
                        self.item_collected.emit(url, 'No data returned', False)
                except Exception as e:
                    self.item_collected.emit(url, str(e), False)
                
                self.progress_updated.emit(idx + 1, total)
                
        finally:
            await crawler.close()
    
    def stop(self):
        """Stop crawler"""
        self.is_running = False


class KeywordSearchWorker(QThread):
    """Background thread for keyword search"""
    progress_updated = pyqtSignal(int, int)
    item_found = pyqtSignal(str, str, int, list)  # url, title, matches, images
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, search_type, query, keyword, config, num_results=10):
        super().__init__()
        self.search_type = search_type
        self.query = query
        self.keyword = keyword
        self.config = config
        self.num_results = num_results
        self.is_running = True
        
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.run_search())
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()
    
    async def run_search(self):
        from modules.keyword_search import KeywordSearcher
        
        db_path = self.config['db']['path']
        await init_db(db_path)
        
        save_images = self.config.get('keyword_search', {}).get('save_images', True)
        
        async with KeywordSearcher(save_images=save_images) as searcher:
            if self.search_type == 'google':
                results = await searcher.search_google(self.keyword, self.num_results)
            elif self.search_type == 'naver':
                results = await searcher.search_naver(self.keyword, self.num_results)
            elif self.search_type == 'urls':
                urls = [url.strip() for url in self.query.split('\n') if url.strip()]
                results = await searcher.batch_search(urls, self.keyword, min_matches=1)
            else:
                return
            
            total = len(results)
            for idx, result in enumerate(results):
                if not self.is_running:
                    break
                
                item = {
                    'url': result['url'],
                    'title': result['title'],
                    'content': result.get('snippet', result.get('content', '')),
                    'keyword': self.keyword,
                    'keyword_matches': result.get('keyword_matches', 0),
                    'images': result.get('images', [])
                }
                
                try:
                    await save_item(db_path, item)
                    self.item_found.emit(
                        result['url'],
                        result['title'],
                        result.get('keyword_matches', 0),
                        result.get('images', [])
                    )
                except Exception as e:
                    logger.error(f"Failed to save item: {e}")
                
                self.progress_updated.emit(idx + 1, total)
    
    def stop(self):
        self.is_running = False


class DashboardTab(QWidget):
    """Dashboard tab showing statistics and status"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("📊 대시보드")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Statistics Group
        stats_group = QGroupBox("수집 통계")
        stats_layout = QGridLayout()
        
        self.total_label = QLabel("0")
        self.total_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.today_label = QLabel("0")
        self.today_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.domains_label = QLabel("0")
        self.domains_label.setFont(QFont("Arial", 24, QFont.Bold))
        
        stats_layout.addWidget(QLabel("총 수집 항목:"), 0, 0)
        stats_layout.addWidget(self.total_label, 0, 1)
        stats_layout.addWidget(QLabel("오늘 수집:"), 1, 0)
        stats_layout.addWidget(self.today_label, 1, 1)
        stats_layout.addWidget(QLabel("도메인 수:"), 2, 0)
        stats_layout.addWidget(self.domains_label, 2, 1)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Status Group
        status_group = QGroupBox("시스템 상태")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("🟢 대기 중")
        self.status_label.setFont(QFont("Arial", 12))
        status_layout.addWidget(self.status_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Quick Actions
        actions_group = QGroupBox("빠른 작업")
        actions_layout = QVBoxLayout()
        
        refresh_btn = QPushButton("🔄 통계 새로고침")
        refresh_btn.clicked.connect(self.refresh_stats)
        actions_layout.addWidget(refresh_btn)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Initial load
        self.refresh_stats()
    
    def refresh_stats(self):
        """Refresh statistics from database"""
        try:
            config = load_config_function().to_dict()
            db_path = config['db']['path']
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            stats = loop.run_until_complete(get_stats(db_path))
            loop.close()
            
            self.total_label.setText(str(stats['total_items']))
            self.today_label.setText(str(stats['today_items']))
            self.domains_label.setText(str(stats['unique_domains']))
            
        except Exception as e:
            logger.error(f"Failed to refresh stats: {e}")
    
    def update_status(self, status: str):
        """Update crawler status"""
        self.status_label.setText(status)


class CollectorTab(QWidget):
    """Data collection tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: Optional[CrawlerWorker] = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("🚀 데이터 수집")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # URL Input
        input_group = QGroupBox("수집 URL 입력")
        input_layout = QVBoxLayout()
        
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("수집할 URL을 입력하세요 (한 줄에 하나씩)\n\nhttps://example.com\nhttps://another-site.com")
        self.url_input.setMaximumHeight(150)
        input_layout.addWidget(self.url_input)
        
        # Load from config button
        load_btn = QPushButton("📄 설정에서 불러오기")
        load_btn.clicked.connect(self.load_from_config)
        input_layout.addWidget(load_btn)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Control Buttons
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ 수집 시작")
        self.start_btn.clicked.connect(self.start_collection)
        self.start_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 10px; }")
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ 중지")
        self.stop_btn.clicked.connect(self.stop_collection)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; font-weight: bold; padding: 10px; }")
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
        
        # Progress
        progress_group = QGroupBox("진행 상황")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("0 / 0")
        progress_layout.addWidget(self.progress_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Results
        results_group = QGroupBox("수집 결과")
        results_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        results_layout.addWidget(self.results_text)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def load_from_config(self):
        """Load URLs from config file"""
        try:
            config = load_config_function().to_dict()
            urls = config.get('targets', []) + config.get('rss_feeds', [])
            self.url_input.setText('\n'.join(urls))
        except Exception as e:
            QMessageBox.warning(self, "오류", f"설정 파일 로드 실패: {e}")
    
    def start_collection(self):
        """Start data collection"""
        urls_text = self.url_input.toPlainText()
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        if not urls:
            QMessageBox.warning(self, "경고", "최소 하나의 URL을 입력해주세요.")
            return
        
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "경고", "이미 수집이 진행 중입니다.")
            return
        
        try:
            config = load_config_function().to_dict()
            
            self.results_text.clear()
            self.results_text.append(f"수집 시작: {len(urls)}개 URL\n")
            
            self.worker = CrawlerWorker(urls, config)
            self.worker.progress_updated.connect(self.update_progress)
            self.worker.item_collected.connect(self.add_result)
            self.worker.finished.connect(self.collection_finished)
            self.worker.error_occurred.connect(self.show_error)
            
            self.worker.start()
            
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.progress_bar.setMaximum(len(urls))
            self.progress_bar.setValue(0)
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"수집 시작 실패: {e}")
    
    def stop_collection(self):
        """Stop data collection"""
        if self.worker:
            self.worker.stop()
            self.results_text.append("\n⚠️ 중지 요청됨...")
    
    def update_progress(self, current: int, total: int):
        """Update progress bar"""
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"{current} / {total}")
    
    def add_result(self, url: str, title: str, success: bool):
        """Add collection result"""
        status = "✅" if success else "❌"
        self.results_text.append(f"{status} {title[:50]}")
        self.results_text.append(f"   {url}")
    
    def collection_finished(self):
        """Handle collection completion"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.results_text.append("\n✅ 수집 완료!")
        
        # Refresh dashboard
        if hasattr(self.parent(), 'dashboard_tab'):
            self.parent().dashboard_tab.refresh_stats()
    
    def show_error(self, error_msg: str):
        """Show error message"""
        QMessageBox.critical(self, "오류", f"수집 중 오류 발생:\n{error_msg}")


class DataViewTab(QWidget):
    """Data viewing tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("📋 수집 결과")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Search
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("검색 (제목 또는 URL)")
        search_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("🔍 검색")
        search_btn.clicked.connect(self.search_data)
        search_layout.addWidget(search_btn)
        
        refresh_btn = QPushButton("🔄 새로고침")
        refresh_btn.clicked.connect(self.load_data)
        search_layout.addWidget(refresh_btn)
        
        layout.addLayout(search_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "제목", "URL", "수집 일시"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 300)
        self.table.setColumnWidth(2, 300)
        layout.addWidget(self.table)
        
        # Pagination
        pagination_layout = QHBoxLayout()
        
        self.page_label = QLabel("페이지: 1")
        pagination_layout.addWidget(self.page_label)
        
        prev_btn = QPushButton("◀ 이전")
        prev_btn.clicked.connect(self.prev_page)
        pagination_layout.addWidget(prev_btn)
        
        next_btn = QPushButton("다음 ▶")
        next_btn.clicked.connect(self.next_page)
        pagination_layout.addWidget(next_btn)
        
        pagination_layout.addStretch()
        
        layout.addLayout(pagination_layout)
        
        self.setLayout(layout)
        
        self.current_page = 1
        self.per_page = 50
        self.load_data()
    
    def load_data(self, search: str = ""):
        """Load data from database"""
        try:
            config = load_config_function().to_dict()
            db_path = config['db']['path']
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            offset = (self.current_page - 1) * self.per_page
            items = loop.run_until_complete(
                get_all_items(db_path, limit=self.per_page, offset=offset, search=search)
            )
            loop.close()
            
            self.table.setRowCount(len(items))
            
            for row, item in enumerate(items):
                self.table.setItem(row, 0, QTableWidgetItem(str(item['id'])))
                self.table.setItem(row, 1, QTableWidgetItem(item['title'][:100]))
                self.table.setItem(row, 2, QTableWidgetItem(item['url'][:100]))
                self.table.setItem(row, 3, QTableWidgetItem(item['fetched_at']))
            
            self.page_label.setText(f"페이지: {self.current_page}")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"데이터 로드 실패: {e}")
    
    def search_data(self):
        """Search data"""
        search_text = self.search_input.text()
        self.current_page = 1
        self.load_data(search_text)
    
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_data()
    
    def next_page(self):
        """Go to next page"""
        self.current_page += 1
        self.load_data()


class ConfigTab(QWidget):
    """Configuration tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("⚙️ 설정 관리")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Crawler Settings
        crawler_group = QGroupBox("크롤러 설정")
        crawler_layout = QGridLayout()
        
        crawler_layout.addWidget(QLabel("동시 요청 수:"), 0, 0)
        self.max_concurrent = QSpinBox()
        self.max_concurrent.setRange(1, 20)
        crawler_layout.addWidget(self.max_concurrent, 0, 1)
        
        crawler_layout.addWidget(QLabel("타임아웃 (초):"), 1, 0)
        self.timeout = QSpinBox()
        self.timeout.setRange(5, 60)
        crawler_layout.addWidget(self.timeout, 1, 1)
        
        crawler_layout.addWidget(QLabel("재시도 횟수:"), 2, 0)
        self.max_retries = QSpinBox()
        self.max_retries.setRange(0, 10)
        crawler_layout.addWidget(self.max_retries, 2, 1)
        
        self.use_trafilatura = QCheckBox("본문 추출 사용")
        crawler_layout.addWidget(self.use_trafilatura, 3, 0, 1, 2)
        
        self.use_playwright = QCheckBox("동적 페이지 지원")
        crawler_layout.addWidget(self.use_playwright, 4, 0, 1, 2)
        
        self.respect_robots = QCheckBox("robots.txt 준수")
        crawler_layout.addWidget(self.respect_robots, 5, 0, 1, 2)
        
        crawler_group.setLayout(crawler_layout)
        layout.addWidget(crawler_group)
        
        # Save Button
        save_btn = QPushButton("💾 설정 저장")
        save_btn.clicked.connect(self.save_config)
        save_btn.setStyleSheet("QPushButton { background-color: #007bff; color: white; font-weight: bold; padding: 10px; }")
        layout.addWidget(save_btn)
        
        layout.addStretch()
        self.setLayout(layout)
        
        self.load_config()
    
    def load_config(self):
        """Load configuration"""
        try:
            config = load_config_function().to_dict()
            
            self.max_concurrent.setValue(config['crawler'].get('max_concurrent', 5))
            self.timeout.setValue(config['crawler'].get('timeout', 10))
            self.max_retries.setValue(config['crawler'].get('max_retries', 3))
            self.use_trafilatura.setChecked(config['crawler'].get('use_trafilatura', False))
            self.use_playwright.setChecked(config['crawler'].get('use_playwright', False))
            self.respect_robots.setChecked(config['crawler'].get('respect_robots', True))
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 로드 실패: {e}")
    
    def save_config(self):
        """Save configuration"""
        try:
            import yaml
            
            config_path = Path('config.yaml')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            config['crawler']['max_concurrent'] = self.max_concurrent.value()
            config['crawler']['timeout'] = self.timeout.value()
            config['crawler']['max_retries'] = self.max_retries.value()
            config['crawler']['use_trafilatura'] = self.use_trafilatura.isChecked()
            config['crawler']['use_playwright'] = self.use_playwright.isChecked()
            config['crawler']['respect_robots'] = self.respect_robots.isChecked()
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            QMessageBox.information(self, "성공", "설정이 저장되었습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 저장 실패: {e}")


class LogViewTab(QWidget):
    """Log viewing tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("📄 로그 보기")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Log file selector
        selector_layout = QHBoxLayout()
        
        self.log_combo = QComboBox()
        self.refresh_log_files()
        selector_layout.addWidget(self.log_combo)
        
        refresh_btn = QPushButton("🔄 새로고침")
        refresh_btn.clicked.connect(self.load_log)
        selector_layout.addWidget(refresh_btn)
        
        layout.addLayout(selector_layout)
        
        # Log content
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        layout.addWidget(self.log_text)
        
        self.setLayout(layout)
        
        # Auto-refresh timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.load_log)
        self.timer.start(5000)  # Refresh every 5 seconds
        
        self.load_log()
    
    def refresh_log_files(self):
        """Refresh log file list"""
        log_dir = Path('logs')
        if log_dir.exists():
            log_files = sorted(log_dir.glob('*.log'), key=lambda x: x.stat().st_mtime, reverse=True)
            self.log_combo.clear()
            self.log_combo.addItems([f.name for f in log_files])
    
    def load_log(self):
        """Load log file content"""
        try:
            log_file = self.log_combo.currentText()
            if not log_file:
                return
            
            log_path = Path('logs') / log_file
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Show last 200 lines
                    content = ''.join(lines[-200:])
                    self.log_text.setText(content)
                    
                    # Scroll to bottom
                    scrollbar = self.log_text.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            logger.error(f"Failed to load log: {e}")


class KeywordSearchTab(QWidget):
    """Keyword search tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("🔍 키워드 검색")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Search Type
        type_group = QGroupBox("검색 유형")
        type_layout = QHBoxLayout()
        
        self.search_type = QComboBox()
        self.search_type.addItems(["URL + 키워드", "Google 검색", "Naver 검색"])
        self.search_type.currentIndexChanged.connect(self.on_search_type_changed)
        type_layout.addWidget(self.search_type)
        
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Keyword Input
        keyword_group = QGroupBox("검색 키워드")
        keyword_layout = QVBoxLayout()
        
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("검색할 키워드를 입력하세요 (예: Python, 머신러닝)")
        keyword_layout.addWidget(self.keyword_input)
        
        keyword_group.setLayout(keyword_layout)
        layout.addWidget(keyword_group)
        
        # URL/Query Input
        query_group = QGroupBox("대상 URL 또는 검색어")
        query_layout = QVBoxLayout()
        
        self.query_input = QTextEdit()
        self.query_input.setPlaceholderText("URL 목록 (한 줄에 하나씩) 또는 검색어 입력")
        self.query_input.setMaximumHeight(120)
        query_layout.addWidget(self.query_input)
        
        query_group.setLayout(query_layout)
        layout.addWidget(query_group)
        self.query_group = query_group
        
        # Options
        options_group = QGroupBox("옵션")
        options_layout = QHBoxLayout()
        
        options_layout.addWidget(QLabel("결과 수:"))
        self.num_results = QSpinBox()
        self.num_results.setRange(1, 50)
        self.num_results.setValue(10)
        options_layout.addWidget(self.num_results)
        
        self.save_images_check = QCheckBox("이미지 저장")
        self.save_images_check.setChecked(True)
        options_layout.addWidget(self.save_images_check)
        
        options_layout.addStretch()
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Control Buttons
        btn_layout = QHBoxLayout()
        
        self.search_btn = QPushButton("🔍 검색 시작")
        self.search_btn.clicked.connect(self.start_search)
        self.search_btn.setStyleSheet("QPushButton { background-color: #007bff; color: white; font-weight: bold; padding: 10px; }")
        btn_layout.addWidget(self.search_btn)
        
        self.stop_btn = QPushButton("⏹ 중지")
        self.stop_btn.clicked.connect(self.stop_search)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; font-weight: bold; padding: 10px; }")
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
        
        # Progress
        progress_group = QGroupBox("진행 상황")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("0 / 0")
        progress_layout.addWidget(self.progress_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Results
        results_group = QGroupBox("검색 결과")
        results_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        results_layout.addWidget(self.results_text)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
        self.on_search_type_changed(0)
    
    def on_search_type_changed(self, index):
        if index == 0:
            self.query_group.setTitle("대상 URL 목록")
            self.query_input.setPlaceholderText("수집할 URL을 입력하세요 (한 줄에 하나씩)\n\nhttps://example.com")
        else:
            self.query_group.setTitle("검색어 (선택사항)")
            self.query_input.setPlaceholderText("추가 검색어 또는 비워두기")
    
    def start_search(self):
        keyword = self.keyword_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "경고", "키워드를 입력해주세요.")
            return
        
        search_index = self.search_type.currentIndex()
        query = self.query_input.toPlainText().strip()
        
        if search_index == 0 and not query:
            QMessageBox.warning(self, "경고", "URL을 입력해주세요.")
            return
        
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "경고", "이미 검색이 진행 중입니다.")
            return
        
        try:
            config = load_config_function().to_dict()
            
            if 'keyword_search' not in config:
                config['keyword_search'] = {}
            config['keyword_search']['save_images'] = self.save_images_check.isChecked()
            
            search_types = ['urls', 'google', 'naver']
            search_type = search_types[search_index]
            
            if search_type in ['google', 'naver']:
                query = keyword
            
            self.results_text.clear()
            self.results_text.append(f"🔍 '{keyword}' 검색 시작...\n")
            
            self.worker = KeywordSearchWorker(
                search_type, query, keyword, config, self.num_results.value()
            )
            
            self.worker.progress_updated.connect(self.update_progress)
            self.worker.item_found.connect(self.add_result)
            self.worker.finished.connect(self.search_finished)
            self.worker.error_occurred.connect(self.show_error)
            
            self.worker.start()
            
            self.search_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.progress_bar.setValue(0)
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"검색 시작 실패: {e}")
    
    def stop_search(self):
        if self.worker:
            self.worker.stop()
            self.results_text.append("\n⚠️ 중지 요청됨...")
    
    def update_progress(self, current: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"{current} / {total}")
    
    def add_result(self, url: str, title: str, matches: int, images: list):
        self.results_text.append(f"✅ {title[:60]}")
        self.results_text.append(f"   URL: {url}")
        if matches > 0:
            self.results_text.append(f"   매칭: {matches}회")
        if images:
            self.results_text.append(f"   이미지: {len(images)}개 저장됨")
        self.results_text.append("")
    
    def search_finished(self):
        self.search_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.results_text.append("\n✅ 검색 완료!")
    
    def show_error(self, error_msg: str):
        QMessageBox.critical(self, "오류", f"검색 중 오류 발생:\n{error_msg}")


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Data Collector - Desktop GUI")
        self.setGeometry(100, 100, 1000, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Tab widget
        tabs = QTabWidget()
        
        # Add tabs
        self.collector_tab = CollectorTab()
        tabs.addTab(self.collector_tab, "🚀 데이터 수집")
        
        data_tab = DataViewTab()
        tabs.addTab(data_tab, "📋 수집 결과")
        
        keyword_search_tab = KeywordSearchTab()
        tabs.addTab(keyword_search_tab, "🔍 키워드 검색")
        
        self.dashboard_tab = DashboardTab()
        tabs.addTab(self.dashboard_tab, "📊 대시보드")
        
        config_tab = ConfigTab()
        tabs.addTab(config_tab, "⚙️ 설정")
        
        log_tab = LogViewTab()
        tabs.addTab(log_tab, "📄 로그")
        
        layout.addWidget(tabs)
        
        # Status bar
        self.statusBar().showMessage("준비 완료")
        
        # Apply modern style
        self.apply_style()
    
    def apply_style(self):
        """Apply modern UI style"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                border-radius: 5px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: #e0e0e0;
                border: 1px solid #cccccc;
                padding: 10px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: white;
                font-weight: bold;
            }
        """)


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
