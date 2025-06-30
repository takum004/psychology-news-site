"""
RSS feed collector for gathering articles from psychology-related media.
"""

import asyncio
import aiohttp
import feedparser
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .base_collector import BaseCollector

class RSSCollector(BaseCollector):
    """RSS フィードからの記事収集"""
    
    # 信頼できる心理学系メディアのRSSフィード
    DEFAULT_FEEDS = [
        {
            'name': 'Psychology Today',
            'url': 'https://www.psychologytoday.com/rss',
            'category': 'general'
        },
        {
            'name': 'American Psychological Association',
            'url': 'https://www.apa.org/news/rss/index.aspx',
            'category': 'research'
        },
        {
            'name': 'Scientific American Mind',
            'url': 'https://www.scientificamerican.com/xml/rss.xml',
            'category': 'research'
        },
        {
            'name': 'PsyPost',
            'url': 'https://www.psypost.org/feed',
            'category': 'research'
        }
    ]
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.feeds = config.get('rss_feeds', self.DEFAULT_FEEDS)
        self.session = None
    
    async def collect(self, query: str = "", limit: int = 20) -> List[Dict]:
        """RSS フィードから記事を収集"""
        all_articles = []
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            self.session = session
            
            # 各フィードから並列で収集
            tasks = []
            for feed in self.feeds:
                task = self._collect_from_feed(feed, limit // len(self.feeds) + 1)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 結果をマージ
            for result in results:
                if isinstance(result, list):
                    all_articles.extend(result)
                elif isinstance(result, Exception):
                    self.logger.error(f"Feed collection error: {result}")
        
        # 重複排除とフィルタリング
        unique_articles = self.deduplicate(all_articles)
        
        # クエリフィルタリング（もし指定されていれば）
        if query:
            unique_articles = self._filter_by_query(unique_articles, query)
        
        # 日付でソートして最新のものを返す
        sorted_articles = sorted(
            unique_articles,
            key=lambda x: x.get('published_date', ''),
            reverse=True
        )
        
        return sorted_articles[:limit]
    
    async def _collect_from_feed(self, feed: Dict, limit: int) -> List[Dict]:
        """単一のRSSフィードから収集"""
        try:
            self.logger.info(f"Collecting from feed: {feed['name']}")
            
            async with self.session.get(feed['url']) as response:
                if response.status != 200:
                    self.logger.warning(f"Failed to fetch {feed['name']}: {response.status}")
                    return []
                
                content = await response.text()
                return self._parse_feed(content, feed)
        
        except Exception as e:
            self.logger.error(f"Error collecting from {feed['name']}: {e}")
            return []
    
    def _parse_feed(self, content: str, feed: Dict) -> List[Dict]:
        """フィードコンテンツの解析"""
        try:
            parsed_feed = feedparser.parse(content)
            articles = []
            
            for entry in parsed_feed.entries[:20]:  # 最大20記事
                article = self._parse_entry(entry, feed)
                if article and self.validate_article(article):
                    articles.append(article)
            
            return articles
        
        except Exception as e:
            self.logger.error(f"Error parsing feed {feed['name']}: {e}")
            return []
    
    def _parse_entry(self, entry, feed: Dict) -> Optional[Dict]:
        """フィードエントリの解析"""
        try:
            # 日付の処理
            published_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                dt = datetime(*entry.published_parsed[:6])
                published_date = dt.strftime('%Y-%m-%d')
            elif hasattr(entry, 'published'):
                published_date = self.extract_date(entry.published)
            
            # 1週間以内の記事のみを対象
            if published_date:
                pub_dt = datetime.strptime(published_date, '%Y-%m-%d')
                if (datetime.now() - pub_dt).days > 7:
                    return None
            
            # 要約/概要の取得
            summary = ""
            if hasattr(entry, 'summary'):
                summary = self.sanitize_text(entry.summary)
            elif hasattr(entry, 'description'):
                summary = self.sanitize_text(entry.description)
            
            # 心理学関連キーワードのチェック
            if not self._is_psychology_related(entry.title + " " + summary):
                return None
            
            return {
                'source': 'rss',
                'feed_name': feed['name'],
                'category': feed['category'],
                'title': self.sanitize_text(entry.title),
                'url': entry.link,
                'summary': summary,
                'published_date': published_date or datetime.now().strftime('%Y-%m-%d'),
                'author': getattr(entry, 'author', ''),
                'tags': [tag.term for tag in getattr(entry, 'tags', [])],
                'collected_at': datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Error parsing entry: {e}")
            return None
    
    def _is_psychology_related(self, text: str) -> bool:
        """心理学関連の記事かどうかを判定"""
        psychology_keywords = [
            'psychology', 'psychological', 'psychologist',
            'mental health', 'behavior', 'behavioural', 'cognitive',
            'therapy', 'depression', 'anxiety', 'stress',
            'mindfulness', 'wellbeing', 'happiness', 'motivation',
            'personality', 'emotion', 'social psychology',
            'research', 'study', 'experiment', 'brain',
            '心理学', '心理', 'メンタル', '行動', '認知',
            'ストレス', '不安', 'うつ', '幸福', 'モチベーション'
        ]
        
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in psychology_keywords)
    
    def _filter_by_query(self, articles: List[Dict], query: str) -> List[Dict]:
        """クエリによる記事フィルタリング"""
        if not query:
            return articles
        
        query_lower = query.lower()
        filtered = []
        
        for article in articles:
            title = article.get('title', '').lower()
            summary = article.get('summary', '').lower()
            
            if query_lower in title or query_lower in summary:
                filtered.append(article)
        
        return filtered
    
    def parse_response(self, response: Dict) -> List[Dict]:
        """RSS collector では使用しない"""
        return []