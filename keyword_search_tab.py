# Keyword Search Tab for desktop_gui.py

class KeywordSearchWorker(QThread):
    """Background thread for keyword search"""
    progress_updated = pyqtSignal(int, int)
    item_found = pyqtSignal(str, str, int, list)  # url, title, matches, images
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, search_type, query, keyword, config, num_results=10):
        super().__init__()
        self.search_type = search_type  # 'google', 'naver', 'urls'
        self.query = query  # keyword or URLs
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
        from modules.database import init_db, save_item
        
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
                
                # Save to database
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


class KeywordSearchTab(QWidget):
    """Keyword search tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
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
        
        # Initialize UI state
        self.on_search_type_changed(0)
    
    def on_search_type_changed(self, index):
        """Update UI based on search type"""
        if index == 0:  # URL + 키워드
            self.query_group.setTitle("대상 URL 목록")
            self.query_input.setPlaceholderText("수집할 URL을 입력하세요 (한 줄에 하나씩)\n\nhttps://example.com\nhttps://another-site.com")
        else:  # Google/Naver
            self.query_group.setTitle("검색어 (선택사항)")
            self.query_input.setPlaceholderText("추가 검색어 또는 비워두기 (키워드로만 검색)")
    
    def start_search(self):
        """Start keyword search"""
        keyword = self.keyword_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "경고", "키워드를 입력해주세요.")
            return
        
        search_index = self.search_type.currentIndex()
        query = self.query_input.toPlainText().strip()
        
        if search_index == 0 and not query:  # URL + 키워드
            QMessageBox.warning(self, "경고", "URL을 입력해주세요.")
            return
        
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "경고", "이미 검색이 진행 중입니다.")
            return
        
        try:
            config = load_config_function().to_dict()
            
            # Add keyword_search config
            if 'keyword_search' not in config:
                config['keyword_search'] = {}
            config['keyword_search']['save_images'] = self.save_images_check.isChecked()
            
            search_types = ['urls', 'google', 'naver']
            search_type = search_types[search_index]
            
            if search_type in ['google', 'naver']:
                query = keyword  # Use keyword as query for search engines
            
            self.results_text.clear()
            self.results_text.append(f"🔍 '{keyword}' 검색 시작...\n")
            
            self.worker = KeywordSearchWorker(
                search_type,
                query,
                keyword,
                config,
                self.num_results.value()
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
        """Stop search"""
        if self.worker:
            self.worker.stop()
            self.results_text.append("\n⚠️ 중지 요청됨...")
    
    def update_progress(self, current: int, total: int):
        """Update progress bar"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"{current} / {total}")
    
    def add_result(self, url: str, title: str, matches: int, images: list):
        """Add search result"""
        self.results_text.append(f"✅ {title[:60]}")
        self.results_text.append(f"   URL: {url}")
        if matches > 0:
            self.results_text.append(f"   매칭: {matches}회")
        if images:
            self.results_text.append(f"   이미지: {len(images)}개 저장됨")
        self.results_text.append("")
    
    def search_finished(self):
        """Handle search completion"""
        self.search_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.results_text.append("\n✅ 검색 완료!")
    
    def show_error(self, error_msg: str):
        """Show error message"""
        QMessageBox.critical(self, "오류", f"검색 중 오류 발생:\n{error_msg}")
