import sqlite3

conn = sqlite3.connect('data.db')
cursor = conn.cursor()

# 테이블 구조 확인
cursor.execute("PRAGMA table_info(items)")
columns = cursor.fetchall()
print('📋 테이블 구조:')
for col in columns:
    print(f'  - {col[1]} ({col[2]})')

# 총 항목 수
cursor.execute('SELECT COUNT(*) FROM items')
total = cursor.fetchone()[0]
print(f'\n📊 총 항목 수: {total}')

# 최근 10개 항목
cursor.execute('SELECT url, title, fetched_at FROM items ORDER BY fetched_at DESC LIMIT 10')
print('\n📝 최근 10개 항목:')
for idx, (url, title, fetched_at) in enumerate(cursor.fetchall(), 1):
    title_display = title[:60] if title else "제목 없음"
    print(f'{idx:2d}. {title_display:<60} | {fetched_at}')
    print(f'    URL: {url[:80]}')

# 날짜별 통계
cursor.execute('SELECT COUNT(*) as cnt, DATE(fetched_at) as date FROM items GROUP BY date ORDER BY date DESC LIMIT 5')
print('\n📅 날짜별 수집 통계:')
for count, date in cursor.fetchall():
    print(f'  {date}: {count}개')

conn.close()
