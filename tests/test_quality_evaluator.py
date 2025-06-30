"""
Tests for quality evaluator functionality.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from evaluator.quality_evaluator import QualityEvaluator, EvaluationResult

class TestQualityEvaluator:
    """Test quality evaluator functionality."""
    
    @pytest.fixture
    def evaluator(self):
        """Create quality evaluator instance."""
        return QualityEvaluator()
    
    def test_identify_study_type_meta_analysis(self, evaluator):
        """Test meta-analysis study type identification."""
        article = {
            'title': 'A meta-analysis of mindfulness interventions',
            'abstract': 'We conducted a meta-analysis of 50 randomized controlled trials...',
            'publication_types': ['Meta-Analysis']
        }
        
        study_type = evaluator._identify_study_type(article)
        assert study_type == 'meta-analysis'
    
    def test_identify_study_type_rct(self, evaluator):
        """Test RCT study type identification."""
        article = {
            'title': 'Randomized controlled trial of therapy',
            'abstract': 'This randomized controlled trial investigated...',
            'publication_types': ['Randomized Controlled Trial']
        }
        
        study_type = evaluator._identify_study_type(article)
        assert study_type == 'rct'
    
    def test_extract_sample_size(self, evaluator):
        """Test sample size extraction."""
        test_cases = [
            ("Study included 1,500 participants", 1500),
            ("n = 250 subjects", 250),
            ("Sample size was 1000", 1000),
            ("Total of 3,456 individuals", 3456),
            ("Recruited 89 people", 89),
            ("No sample size mentioned", None)
        ]
        
        for text, expected in test_cases:
            article = {'abstract': text}
            result = evaluator._extract_sample_size(article)
            assert result == expected, f"Failed for text: {text}"
    
    def test_extract_effect_size(self, evaluator):
        """Test effect size extraction."""
        test_cases = [
            ("Cohen's d = 0.5", 0.5),
            ("effect size d = 0.8", 0.8),
            ("Hedge's g = -0.3", -0.3),
            ("r = 0.6", 1.5),  # Converted value
            ("No effect size", None)
        ]
        
        for text, expected in test_cases:
            article = {'abstract': text}
            result = evaluator._extract_effect_size(article)
            if expected is None:
                assert result is None
            else:
                assert abs(result - expected) < 0.1, f"Failed for text: {text}"
    
    def test_evaluate_high_quality_study(self, evaluator):
        """Test evaluation of high-quality study."""
        article = {
            'title': 'Meta-analysis of mindfulness interventions',
            'abstract': '''
            We conducted a meta-analysis of 87 randomized controlled trials 
            with n = 15,000 participants. Cohen's d = 0.68 (95% CI: 0.52-0.84).
            The intervention was safe with no adverse effects reported.
            ''',
            'published_date': '2024-01-01',
            'journal': 'Psychological Science',
            'publication_types': ['Meta-Analysis']
        }
        
        result = evaluator.evaluate(article)
        
        assert isinstance(result, EvaluationResult)
        assert result.total_score >= 70
        assert result.evidence_level in ['gold', 'silver']
        assert result.study_type == 'meta-analysis'
        assert result.sample_size == 15000
        assert abs(result.effect_size - 0.68) < 0.01
    
    def test_evaluate_low_quality_study(self, evaluator):
        """Test evaluation of low-quality study."""
        article = {
            'title': 'Case study of one patient',
            'abstract': '''
            We report a case study of one patient who showed improvement.
            No statistical analysis was performed.
            ''',
            'published_date': '2020-01-01',  # Older study
            'journal': 'Unknown Journal',
            'publication_types': ['Case Reports']
        }
        
        result = evaluator.evaluate(article)
        
        assert isinstance(result, EvaluationResult)
        assert result.total_score < 70
        assert result.evidence_level == 'bronze'
        assert result.study_type == 'case report'
    
    def test_evaluate_recency_scoring(self, evaluator):
        """Test recency scoring."""
        from datetime import datetime, timedelta
        
        # Recent study
        recent_date = datetime.now() - timedelta(days=30)
        recent_article = {
            'title': 'Recent study',
            'abstract': 'Recent research findings',
            'published_date': recent_date.strftime('%Y-%m-%d')
        }
        
        recent_score = evaluator._evaluate_recency(recent_article)
        assert recent_score == 10
        
        # Old study
        old_date = datetime.now() - timedelta(days=2000)
        old_article = {
            'title': 'Old study',
            'abstract': 'Old research findings',
            'published_date': old_date.strftime('%Y-%m-%d')
        }
        
        old_score = evaluator._evaluate_recency(old_article)
        assert old_score <= 5
    
    def test_evaluate_safety_scoring(self, evaluator):
        """Test safety evaluation."""
        safe_article = {
            'abstract': 'The intervention was safe with no adverse effects reported.'
        }
        safety_score = evaluator._evaluate_safety(safe_article)
        assert safety_score == 10
        
        risky_article = {
            'abstract': 'Several adverse effects and risks were reported.'
        }
        risk_score = evaluator._evaluate_safety(risky_article)
        assert risk_score == 5
    
    def test_has_power_analysis(self, evaluator):
        """Test power analysis detection."""
        with_power = {
            'abstract': 'Power analysis indicated adequate sample size.'
        }
        assert evaluator._has_power_analysis(with_power)
        
        without_power = {
            'abstract': 'No power analysis mentioned.'
        }
        assert not evaluator._has_power_analysis(without_power)

if __name__ == '__main__':
    pytest.main([__file__])