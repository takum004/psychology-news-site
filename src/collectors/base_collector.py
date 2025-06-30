"""
Base collector class for all data collection modules.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import hashlib
import logging
import json

class BaseCollector(ABC):
    """データ収集の基底クラス"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = self._setup_logger()
        self.cache = {}
    
    def _setup_logger(self) -> logging.Logger:
        """ロガーの設定"""
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.INFO)
        
        # ハンドラが既に追加されている場合はスキップ
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    @abstractmethod
    async def collect(self, query: str, limit: int = 10) -> List[Dict]:
        """データ収集の抽象メソッド"""
        pass
    
    @abstractmethod
    def parse_response(self, response: Dict) -> List[Dict]:
        """レスポンス解析の抽象メソッド"""
        pass
    
    def validate_article(self, article: Dict) -> bool:
        """記事の基本検証"""
        required_fields = ['title', 'url', 'published_date']
        return all(field in article and article[field] for field in required_fields)
    
    def deduplicate(self, articles: List[Dict]) -> List[Dict]:
        """重複排除"""
        seen = set()
        unique_articles = []
        
        for article in articles:
            identifier = self._generate_article_hash(article)
            if identifier not in seen:
                seen.add(identifier)
                unique_articles.append(article)
        
        return unique_articles
    
    def _generate_article_hash(self, article: Dict) -> str:
        """記事のハッシュ生成"""
        content = f"{article.get('title', '')}_{article.get('url', '')}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def sanitize_text(self, text: str) -> str:
        """テキストのサニタイズ"""
        if not text:
            return ""
        
        # HTMLタグの除去（簡易版）
        import re
        text = re.sub(r'<[^>]+>', '', text)
        
        # 余分な空白の除去
        text = ' '.join(text.split())
        
        return text.strip()
    
    def extract_date(self, date_str: str) -> Optional[str]:
        """日付文字列の標準化"""
        try:
            # 様々な日付フォーマットに対応
            from dateutil import parser
            dt = parser.parse(date_str)
            return dt.strftime('%Y-%m-%d')
        except:
            return None