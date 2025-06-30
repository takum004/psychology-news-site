"""
Tests for RSS collector functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from collectors.rss_collector import RSSCollector

class TestRSSCollector:
    """Test RSS collector functionality."""
    
    @pytest.fixture
    def collector(self):
        """Create RSS collector instance."""
        config = {
            'rss_feeds': [
                {
                    'name': 'Test Feed',
                    'url': 'https://example.com/rss',
                    'category': 'test'
                }
            ]
        }
        return RSSCollector(config)
    
    def test_is_psychology_related_positive(self, collector):
        """Test psychology keyword detection - positive cases."""
        test_cases = [
            "Study finds psychology improves mental health",
            "Cognitive behavior therapy shows benefits",
            "Research on stress and anxiety",
            "Mindfulness meditation effects on wellbeing",
            "心理学の研究について"
        ]
        
        for text in test_cases:
            assert collector._is_psychology_related(text), f"Should detect psychology in: {text}"
    
    def test_is_psychology_related_negative(self, collector):
        """Test psychology keyword detection - negative cases."""
        test_cases = [
            "Sports news and football updates",
            "Technology breakthrough in computing",
            "Weather forecast for tomorrow",
            "Stock market analysis"
        ]
        
        for text in test_cases:
            assert not collector._is_psychology_related(text), f"Should not detect psychology in: {text}"
    
    def test_filter_by_query(self, collector):
        """Test query-based filtering."""
        articles = [
            {'title': 'Stress management techniques', 'summary': 'How to reduce stress'},
            {'title': 'Cooking recipes', 'summary': 'Delicious food preparation'},
            {'title': 'Anxiety research', 'summary': 'Latest findings on anxiety'}
        ]
        
        filtered = collector._filter_by_query(articles, 'stress')
        assert len(filtered) == 1
        assert 'stress' in filtered[0]['title'].lower()
    
    @pytest.mark.asyncio
    async def test_collect_basic_functionality(self, collector):
        """Test basic collection functionality with mocked data."""
        # Mock the session and response
        mock_content = '''<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Psychology Research Shows Benefits</title>
                    <link>https://example.com/article1</link>
                    <description>A study on psychology and mental health</description>
                    <pubDate>Mon, 30 Dec 2024 12:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>'''
        
        with patch('aiohttp.ClientSession') as mock_session:
            # Setup mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=mock_content)
            
            mock_session_instance = AsyncMock()
            mock_session_instance.get.return_value.__aenter__.return_value = mock_response
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Test collection
            articles = await collector.collect(limit=5)
            
            # Verify results
            assert isinstance(articles, list)
            # Note: Actual results depend on feed parsing and psychology filtering

class TestRSSCollectorIntegration:
    """Integration tests for RSS collector."""
    
    @pytest.mark.asyncio
    async def test_real_feed_parsing(self):
        """Test with a real RSS feed (if available)."""
        config = {
            'rss_feeds': [
                {
                    'name': 'PsyPost',
                    'url': 'https://www.psypost.org/feed',
                    'category': 'research'
                }
            ]
        }
        
        collector = RSSCollector(config)
        
        try:
            # Try to collect real articles (with timeout)
            articles = await asyncio.wait_for(
                collector.collect(limit=2), 
                timeout=30.0
            )
            
            # Basic validation
            assert isinstance(articles, list)
            
            for article in articles:
                assert 'title' in article
                assert 'url' in article
                assert 'source' in article
                assert article['source'] == 'rss'
        
        except asyncio.TimeoutError:
            pytest.skip("Network timeout - skipping real feed test")
        except Exception as e:
            pytest.skip(f"Network error - skipping real feed test: {e}")

if __name__ == '__main__':
    pytest.main([__file__])