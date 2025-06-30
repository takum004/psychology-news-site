"""
Data collection modules for gathering psychology research articles.
"""

from .base_collector import BaseCollector
from .pubmed_collector import PubMedCollector
from .rss_collector import RSSCollector

__all__ = ['BaseCollector', 'PubMedCollector', 'RSSCollector']