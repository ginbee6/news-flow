from flask import Flask, jsonify, render_template
import feedparser
import requests
from datetime import datetime
import time
import html
import re

app = Flask(__name__)

# キャッシュ（5分間）
_cache = {}
CACHE_TTL = 300

RSS_FEEDS = {
    "world": [
        ("NHK 国際", "https://www3.nhk.or.jp/rss/news/cat0.xml"),
        ("Reuters 日本語", "https://feeds.reuters.com/reuters/JPTopNews"),
    ],
    "soccer": [
        ("Goal.com 日本語", "https://www.goal.com/jp/feeds/news"),
        ("サッカーキング", "https://www.soccer-king.jp/feed"),
        ("スポーツナビ サッカー", "https://sports.yahoo.co.jp/rss/soccer/"),
    ],
    "sports": [
        ("NHK スポーツ", "https://www3.nhk.or.jp/rss/news/cat7.xml"),
        ("スポニチ MLB", "https://www.sponichi.co.jp/baseball/rss/sponichirss20090406185935.html"),
        ("スポーツナビ 野球", "https://sports.yahoo.co.jp/rss/baseball/"),
        ("日刊スポーツ", "https://www.nikkansports.com/rss/baseball/mlb/news/mlb-bb-n0-rss.xml"),
    ],
    "trends": [
        ("Yahoo! Japan トピックス", "https://news.yahoo.co.jp/rss/topics/top-picks.xml"),
        ("NHK 国内", "https://www3.nhk.or.jp/rss/news/cat1.xml"),
        ("はてなブックマーク ホットエントリ", "https://b.hatena.ne.jp/hotentry.rss"),
    ],
}

CATEGORY_LABELS = {
    "world": "世界情勢",
    "soccer": "サッカー",
    "sports": "スポーツ",
    "trends": "SNSトレンド",
}

def clean_html(text):
    text = re.sub(r'<[^>]+>', '', text or '')
    return html.unescape(text).strip()

def parse_date(entry):
    for attr in ('published_parsed', 'updated_parsed'):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6])
            except Exception:
                pass
    return datetime.now()

def fetch_feed(url, source_name, category):
    try:
        feed = feedparser.parse(url, agent='Mozilla/5.0')
        articles = []
        for entry in feed.entries[:10]:
            title = clean_html(entry.get('title', ''))
            summary = clean_html(entry.get('summary', entry.get('description', '')))
            link = entry.get('link', '')
            pub_date = parse_date(entry)
            image = None
            if hasattr(entry, 'media_content') and entry.media_content:
                image = entry.media_content[0].get('url')
            if not image and hasattr(entry, 'enclosures') and entry.enclosures:
                for enc in entry.enclosures:
                    if 'image' in enc.get('type', ''):
                        image = enc.get('href')
                        break
            if title:
                articles.append({
                    'title': title,
                    'summary': summary[:120] + '…' if len(summary) > 120 else summary,
                    'link': link,
                    'source': source_name,
                    'category': category,
                    'category_label': CATEGORY_LABELS.get(category, category),
                    'published': pub_date.isoformat(),
                    'published_ts': pub_date.timestamp(),
                    'image': image,
                })
        return articles
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def get_news(category='all'):
    cache_key = category
    now = time.time()
    if cache_key in _cache and now - _cache[cache_key]['ts'] < CACHE_TTL:
        return _cache[cache_key]['data']

    articles = []
    cats = list(RSS_FEEDS.keys()) if category == 'all' else [category]
    for cat in cats:
        if cat not in RSS_FEEDS:
            continue
        for source_name, url in RSS_FEEDS[cat]:
            articles.extend(fetch_feed(url, source_name, cat))

    articles.sort(key=lambda x: x['published_ts'], reverse=True)
    _cache[cache_key] = {'ts': now, 'data': articles}
    return articles

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/news')
def api_news():
    from flask import request
    category = request.args.get('category', 'all')
    articles = get_news(category)
    return jsonify({'articles': articles, 'count': len(articles)})

if __name__ == '__main__':
    print("ニュースアプリを起動中... http://localhost:5000")
    app.run(debug=True, port=5000)
