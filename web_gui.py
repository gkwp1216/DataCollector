"""
Web GUI for Data Collector
Flask-based dashboard for managing and monitoring the crawler
"""

import asyncio
import json
import os
import threading
from datetime import datetime
from pathlib import Path

import yaml
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.exceptions import BadRequest

from modules.crawler import AsyncCrawler
from modules.database import init_db, save_item, get_all_items, get_stats
from modules.config_loader import load_config as load_config_function
from modules.logger import get_logger

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Global state
crawler_state = {
    'running': False,
    'thread': None,
    'results': [],
    'errors': [],
    'progress': 0,
    'total': 0
}

logger = get_logger(__name__)


def load_config():
    """Load configuration"""
    config_loader = load_config_function()
    return config_loader.to_dict()


def save_config(config_data):
    """Save configuration to config.yaml"""
    config_path = Path('config.yaml')
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)


async def run_crawler_async(urls, config):
    """Run crawler asynchronously"""
    try:
        db_path = config['db']['path']
        await init_db(db_path)
        
        crawler = AsyncCrawler(
            timeout=config['crawler'].get('timeout', 10),
            max_retries=config['crawler'].get('max_retries', 3),
            use_trafilatura=config['crawler'].get('use_trafilatura', False),
            use_playwright=config['crawler'].get('use_playwright', False),
            respect_robots=config['crawler'].get('respect_robots', True)
        )
        
        crawler_state['total'] = len(urls)
        crawler_state['progress'] = 0
        crawler_state['results'] = []
        crawler_state['errors'] = []
        
        try:
            for idx, url in enumerate(urls):
                if not crawler_state['running']:
                    logger.info("Crawler stopped by user")
                    break
                
                try:
                    data = await crawler.fetch_and_parse(url)
                    if data:
                        await save_item(db_path, data)
                        crawler_state['results'].append({
                            'url': url,
                            'title': data.get('title', 'No title'),
                            'status': 'success'
                        })
                        logger.info(f"Successfully collected: {url}")
                    else:
                        crawler_state['errors'].append({
                            'url': url,
                            'error': 'No data returned'
                        })
                except Exception as e:
                    error_msg = str(e)
                    crawler_state['errors'].append({
                        'url': url,
                        'error': error_msg
                    })
                    logger.error(f"Error collecting {url}: {error_msg}")
                
                crawler_state['progress'] = idx + 1
                
        finally:
            await crawler.close()
            
    except Exception as e:
        logger.error(f"Crawler error: {e}", exc_info=True)
        crawler_state['errors'].append({
            'url': 'system',
            'error': str(e)
        })
    finally:
        crawler_state['running'] = False


def run_crawler_thread(urls, config):
    """Run crawler in thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_crawler_async(urls, config))
    finally:
        loop.close()


@app.route('/')
def index():
    """Dashboard home page"""
    config = load_config()
    
    # Get database stats
    db_path = config['db']['path']
    stats = asyncio.run(get_stats(db_path))
    
    return render_template('index.html', 
                          config=config, 
                          stats=stats,
                          crawler_state=crawler_state)


@app.route('/collect', methods=['GET', 'POST'])
def collect():
    """Data collection page"""
    if request.method == 'POST':
        urls_text = request.form.get('urls', '')
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        if not urls:
            flash('최소 하나의 URL을 입력해주세요.', 'error')
            return redirect(url_for('collect'))
        
        if crawler_state['running']:
            flash('크롤러가 이미 실행 중입니다.', 'warning')
            return redirect(url_for('collect'))
        
        # Start crawler in background thread
        config = load_config()
        crawler_state['running'] = True
        thread = threading.Thread(target=run_crawler_thread, args=(urls, config))
        thread.daemon = True
        thread.start()
        crawler_state['thread'] = thread
        
        flash(f'{len(urls)}개의 URL 수집을 시작했습니다.', 'success')
        return redirect(url_for('progress'))
    
    config = load_config()
    return render_template('collect.html', config=config)


@app.route('/progress')
def progress():
    """Collection progress page"""
    return render_template('progress.html', crawler_state=crawler_state)


@app.route('/api/progress')
def api_progress():
    """API endpoint for progress updates"""
    return jsonify({
        'running': crawler_state['running'],
        'progress': crawler_state['progress'],
        'total': crawler_state['total'],
        'results_count': len(crawler_state['results']),
        'errors_count': len(crawler_state['errors']),
        'results': crawler_state['results'][-10:],  # Last 10 results
        'errors': crawler_state['errors'][-10:]  # Last 10 errors
    })


@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Stop crawler"""
    crawler_state['running'] = False
    return jsonify({'status': 'stopping'})


@app.route('/data')
def data():
    """View collected data"""
    config = load_config()
    db_path = config['db']['path']
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search = request.args.get('search', '')
    
    items = asyncio.run(get_all_items(db_path, limit=per_page, offset=(page-1)*per_page, search=search))
    stats = asyncio.run(get_stats(db_path))
    
    return render_template('data.html', 
                          items=items, 
                          stats=stats,
                          page=page,
                          per_page=per_page,
                          search=search)


@app.route('/config', methods=['GET', 'POST'])
def config_page():
    """Configuration management page"""
    if request.method == 'POST':
        try:
            # Update configuration
            config = load_config()
            
            # Update crawler settings
            config['crawler']['max_concurrent'] = int(request.form.get('max_concurrent', 5))
            config['crawler']['timeout'] = int(request.form.get('timeout', 10))
            config['crawler']['max_retries'] = int(request.form.get('max_retries', 3))
            config['crawler']['delay_between_requests'] = float(request.form.get('delay', 1.0))
            config['crawler']['skip_duplicates'] = request.form.get('skip_duplicates') == 'on'
            config['crawler']['use_trafilatura'] = request.form.get('use_trafilatura') == 'on'
            config['crawler']['use_playwright'] = request.form.get('use_playwright') == 'on'
            config['crawler']['respect_robots'] = request.form.get('respect_robots') == 'on'
            
            # Update targets
            targets_text = request.form.get('targets', '')
            config['targets'] = [url.strip() for url in targets_text.split('\n') if url.strip()]
            
            # Update RSS feeds
            rss_text = request.form.get('rss_feeds', '')
            config['rss_feeds'] = [url.strip() for url in rss_text.split('\n') if url.strip()]
            
            # Update logging
            config['logging']['level'] = request.form.get('log_level', 'INFO')
            config['logging']['enable_file_logging'] = request.form.get('enable_file_logging') == 'on'
            config['logging']['enable_console_logging'] = request.form.get('enable_console_logging') == 'on'
            
            # Update scheduler
            config['scheduler']['enabled'] = request.form.get('scheduler_enabled') == 'on'
            config['scheduler']['interval_minutes'] = int(request.form.get('interval_minutes', 60))
            
            # Save configuration
            save_config(config)
            flash('설정이 저장되었습니다.', 'success')
            
        except Exception as e:
            flash(f'설정 저장 실패: {str(e)}', 'error')
            logger.error(f"Config save error: {e}", exc_info=True)
        
        return redirect(url_for('config_page'))
    
    config = load_config()
    return render_template('config.html', config=config)


@app.route('/scheduler')
def scheduler():
    """Scheduler control page"""
    config = load_config()
    return render_template('scheduler.html', config=config)


@app.route('/logs')
def logs():
    """View logs"""
    log_dir = Path('logs')
    log_files = sorted(log_dir.glob('*.log'), key=lambda x: x.stat().st_mtime, reverse=True)
    
    selected_file = request.args.get('file', 'collector.log')
    lines = int(request.args.get('lines', 100))
    
    log_path = log_dir / selected_file
    log_content = ""
    
    if log_path.exists():
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                log_content = ''.join(all_lines[-lines:])
        except Exception as e:
            log_content = f"Error reading log file: {e}"
    
    return render_template('logs.html', 
                          log_files=[f.name for f in log_files],
                          selected_file=selected_file,
                          log_content=log_content,
                          lines=lines)


if __name__ == '__main__':
    # Create logs directory if not exists
    Path('logs').mkdir(exist_ok=True)
    
    # Run Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
