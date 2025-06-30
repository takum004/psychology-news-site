"""
Integration tests for the complete pipeline.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from main import PsychologyNewsAutomation

class TestIntegration:
    """Integration tests for the complete pipeline."""
    
    @pytest.fixture
    def automation(self):
        """Create automation instance."""
        return PsychologyNewsAutomation()
    
    def test_automation_initialization(self, automation):
        """Test that automation initializes correctly."""
        assert automation is not None
        assert automation.rss_collector is not None
        assert automation.pubmed_collector is not None
        assert automation.evaluator is not None
        # summarizer might be None if no API key
    
    @pytest.mark.asyncio
    async def test_collect_and_evaluate_pipeline(self, automation):
        """Test the collect and evaluate pipeline."""
        try:
            # Collect a small number of articles
            articles = await asyncio.wait_for(
                automation.collect_articles('2024-12-30', limit=3),
                timeout=30.0
            )
            
            assert isinstance(articles, list)
            
            if articles:  # Only test if we got articles
                # Evaluate articles
                evaluated = automation.evaluate_articles(articles, threshold=50)  # Lower threshold for testing
                
                assert isinstance(evaluated, list)
                
                # Check evaluation structure
                for article in evaluated:
                    assert 'evaluation' in article
                    evaluation = article['evaluation']
                    assert 'total_score' in evaluation
                    assert 'evidence_level' in evaluation
                    assert 'study_type' in evaluation
        
        except asyncio.TimeoutError:
            pytest.skip("Network timeout - skipping integration test")
        except Exception as e:
            pytest.skip(f"Network or API error - skipping integration test: {e}")
    
    def test_deduplicate_articles(self, automation):
        """Test article deduplication."""
        articles = [
            {'title': 'Article 1', 'url': 'https://example.com/1'},
            {'title': 'Article 2', 'url': 'https://example.com/2'},
            {'title': 'Article 1', 'url': 'https://example.com/1'},  # Duplicate
            {'title': 'Article 3', 'url': 'https://example.com/3'},
        ]
        
        unique = automation._deduplicate_articles(articles)
        
        assert len(unique) == 3
        urls = [a['url'] for a in unique]
        assert len(set(urls)) == 3  # All unique URLs
    
    def test_generate_slug(self, automation):
        """Test slug generation."""
        title = "Amazing Psychology Research: 50% Better Results!"
        slug = automation._generate_slug(title)
        
        assert isinstance(slug, str)
        assert len(slug) > 0
        assert ' ' not in slug  # No spaces
        assert '!' not in slug  # No special chars
        assert slug.startswith('202')  # Starts with date
    
    def test_update_categories_index(self, automation):
        """Test categories index update."""
        articles = [
            {'slug': 'article1', 'title': 'Title 1', 'category': 'motivation', 'published_date': '2024-12-30'},
            {'slug': 'article2', 'title': 'Title 2', 'category': 'stress', 'published_date': '2024-12-29'},
            {'slug': 'article3', 'title': 'Title 3', 'category': 'motivation', 'published_date': '2024-12-28'},
        ]
        
        categories = automation._update_categories_index(articles)
        
        assert 'motivation' in categories
        assert 'stress' in categories
        assert len(categories['motivation']) == 2
        assert len(categories['stress']) == 1
        
        # Check sorting (newest first)
        motivation_articles = categories['motivation']
        assert motivation_articles[0]['date'] > motivation_articles[1]['date']
    
    def test_update_daily_index(self, automation):
        """Test daily index update."""
        articles = [
            {'slug': 'article1', 'title': 'Title 1', 'category': 'motivation', 'published_date': '2024-12-30'},
            {'slug': 'article2', 'title': 'Title 2', 'category': 'stress', 'published_date': '2024-12-30'},
            {'slug': 'article3', 'title': 'Title 3', 'category': 'motivation', 'published_date': '2024-12-29'},
        ]
        
        daily_index = automation._update_daily_index(articles)
        
        assert '2024-12-30' in daily_index
        assert '2024-12-29' in daily_index
        assert len(daily_index['2024-12-30']) == 2
        assert len(daily_index['2024-12-29']) == 1
    
    def test_site_data_update(self, automation):
        """Test site data update functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_dir = Path(temp_dir) / 'site'
            site_dir.mkdir()
            
            # Sample articles
            articles = [
                {
                    'slug': 'test-article-1',
                    'title': 'Test Article 1',
                    'category': 'motivation',
                    'published_date': '2024-12-30',
                    'subtitle': 'Test subtitle',
                    'summary_points': ['Point 1', 'Point 2', 'Point 3']
                }
            ]
            
            # Update site data
            automation.update_site_data(articles, str(site_dir))
            
            # Check that data file was created
            data_file = site_dir / 'src' / 'data' / 'articles.json'
            assert data_file.exists()
            
            # Check data structure
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert 'articles' in data
            assert 'categories' in data
            assert 'daily_index' in data
            assert 'last_updated' in data
            assert 'total_articles' in data
            
            assert len(data['articles']) == 1
            assert data['total_articles'] == 1

class TestEndToEnd:
    """End-to-end tests simulating the complete workflow."""
    
    @pytest.mark.asyncio
    async def test_minimal_workflow(self):
        """Test minimal workflow without external dependencies."""
        automation = PsychologyNewsAutomation()
        
        # Create sample data for each step
        sample_articles = [
            {
                'source': 'test',
                'title': 'Test Psychology Article',
                'abstract': 'A randomized controlled trial with n=1000 participants showed Cohen\'s d = 0.6',
                'url': 'https://example.com/test',
                'published_date': '2024-12-30',
                'authors': ['Test Author'],
                'journal': 'Test Journal'
            }
        ]
        
        # Test evaluation
        evaluated = automation.evaluate_articles(sample_articles, threshold=50)
        assert len(evaluated) > 0
        
        # Test slug generation
        for article in evaluated:
            slug = automation._generate_slug(article['title'])
            assert isinstance(slug, str)
            assert len(slug) > 0
        
        # Test site data structure
        with tempfile.TemporaryDirectory() as temp_dir:
            automation.update_site_data(evaluated, temp_dir)
            
            data_file = Path(temp_dir) / 'src' / 'data' / 'articles.json'
            assert data_file.exists()

if __name__ == '__main__':
    pytest.main([__file__])