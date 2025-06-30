#!/usr/bin/env python3
"""
Main entry point for the psychology news site automation.
"""

import asyncio
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from collectors import RSSCollector, PubMedCollector
from evaluator import QualityEvaluator
from summarizer import OpenAISummarizer

class PsychologyNewsAutomation:
    """Main automation class for the psychology news site."""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.config = self._load_config()
        
        # Initialize components
        self.rss_collector = RSSCollector(self.config)
        self.pubmed_collector = PubMedCollector(self.config)
        self.evaluator = QualityEvaluator()
        
        # Initialize AI summarizer if API key is available
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            self.summarizer = OpenAISummarizer(openai_key)
        else:
            self.summarizer = None
            self.logger.warning("OpenAI API key not found. Summarization will be skipped.")
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('psychology_news.log')
            ]
        )
        return logging.getLogger('PsychologyNews')
    
    def _load_config(self) -> Dict:
        """Load configuration from environment variables."""
        return {
            'pubmed_api_key': os.getenv('PUBMED_API_KEY'),
            'email': os.getenv('EMAIL', 'user@example.com'),
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'rss_feeds': [
                {
                    'name': 'PsyPost',
                    'url': 'https://www.psypost.org/feed',
                    'category': 'research'
                },
                {
                    'name': 'Psychology Today',
                    'url': 'https://www.psychologytoday.com/rss',
                    'category': 'general'
                }
            ]
        }
    
    async def collect_articles(self, date: str, limit: int = 10) -> List[Dict]:
        """Collect articles from various sources."""
        self.logger.info(f"Collecting articles for {date}, limit: {limit}")
        
        all_articles = []
        
        try:
            # Collect from RSS feeds
            self.logger.info("Collecting from RSS feeds...")
            rss_articles = await self.rss_collector.collect(limit=limit//2)
            all_articles.extend(rss_articles)
            self.logger.info(f"Collected {len(rss_articles)} articles from RSS")
            
            # Collect from PubMed
            self.logger.info("Collecting from PubMed...")
            pubmed_articles = await self.pubmed_collector.collect(limit=limit//2)
            all_articles.extend(pubmed_articles)
            self.logger.info(f"Collected {len(pubmed_articles)} articles from PubMed")
            
        except Exception as e:
            self.logger.error(f"Error during collection: {e}")
        
        # Remove duplicates
        unique_articles = self._deduplicate_articles(all_articles)
        self.logger.info(f"Total unique articles collected: {len(unique_articles)}")
        
        return unique_articles[:limit]
    
    def evaluate_articles(self, articles: List[Dict], threshold: int = 70) -> List[Dict]:
        """Evaluate article quality and filter by threshold."""
        self.logger.info(f"Evaluating {len(articles)} articles with threshold {threshold}")
        
        evaluated_articles = []
        
        for article in articles:
            try:
                evaluation = self.evaluator.evaluate(article)
                
                if evaluation.total_score >= threshold:
                    article['evaluation'] = {
                        'total_score': evaluation.total_score,
                        'breakdown': evaluation.breakdown,
                        'evidence_level': evaluation.evidence_level,
                        'study_type': evaluation.study_type,
                        'sample_size': evaluation.sample_size,
                        'effect_size': evaluation.effect_size,
                        'recommendation': evaluation.recommendation
                    }
                    evaluated_articles.append(article)
                    self.logger.debug(f"Article passed: {article.get('title', 'Unknown')[:50]}... (Score: {evaluation.total_score})")
                else:
                    self.logger.debug(f"Article filtered out: {article.get('title', 'Unknown')[:50]}... (Score: {evaluation.total_score})")
            
            except Exception as e:
                self.logger.error(f"Error evaluating article: {e}")
                continue
        
        self.logger.info(f"Articles passed evaluation: {len(evaluated_articles)}")
        return evaluated_articles
    
    async def summarize_articles(self, articles: List[Dict], max_articles: int = 3) -> List[Dict]:
        """Generate AI summaries for articles."""
        if not self.summarizer:
            self.logger.warning("No summarizer available. Skipping summarization.")
            return articles
        
        self.logger.info(f"Summarizing up to {max_articles} articles")
        
        # Sort by quality score and take the best ones
        articles_sorted = sorted(
            articles, 
            key=lambda x: x.get('evaluation', {}).get('total_score', 0), 
            reverse=True
        )
        
        top_articles = articles_sorted[:max_articles]
        summarized_articles = []
        
        for article in top_articles:
            try:
                self.logger.info(f"Summarizing: {article.get('title', 'Unknown')[:50]}...")
                
                evaluation = article.get('evaluation', {})
                summary = await self.summarizer.summarize_article(article, evaluation)
                
                if summary:
                    # Categorize the article
                    category = await self.summarizer.categorize_article(article)
                    summary['category'] = category
                    
                    # Add metadata
                    summary['original_article'] = {
                        'source': article.get('source'),
                        'url': article.get('url'),
                        'published_date': article.get('published_date'),
                        'evaluation': evaluation
                    }
                    
                    # Generate slug
                    summary['slug'] = self._generate_slug(summary['title'])
                    summary['published_date'] = datetime.now().strftime('%Y-%m-%d')
                    
                    summarized_articles.append(summary)
                    self.logger.info("Summary generated successfully")
                else:
                    self.logger.warning("Failed to generate summary")
            
            except Exception as e:
                self.logger.error(f"Error summarizing article: {e}")
                continue
        
        self.logger.info(f"Successfully summarized {len(summarized_articles)} articles")
        return summarized_articles
    
    def update_site_data(self, articles: List[Dict], site_dir: str):
        """Update site data files with new articles."""
        self.logger.info(f"Updating site data in {site_dir}")
        
        site_path = Path(site_dir)
        data_dir = site_path / 'src' / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing data
        articles_file = data_dir / 'articles.json'
        existing_data = self._load_existing_data(articles_file)
        
        # Add new articles
        for article in articles:
            existing_data['articles'].append(article)
        
        # Update metadata
        existing_data['last_updated'] = datetime.now().isoformat()
        existing_data['total_articles'] = len(existing_data['articles'])
        
        # Update categories index
        existing_data['categories'] = self._update_categories_index(existing_data['articles'])
        
        # Update daily index
        existing_data['daily_index'] = self._update_daily_index(existing_data['articles'])
        
        # Save updated data
        with open(articles_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Updated site data with {len(articles)} new articles")
    
    def _deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on URL and title."""
        seen = set()
        unique_articles = []
        
        for article in articles:
            # Create identifier from URL or title
            identifier = article.get('url') or article.get('title', '')
            if identifier and identifier not in seen:
                seen.add(identifier)
                unique_articles.append(article)
        
        return unique_articles
    
    def _generate_slug(self, title: str) -> str:
        """Generate URL slug from title."""
        import re
        from unidecode import unidecode
        
        # Convert to ASCII
        title_ascii = unidecode(title)
        
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', title_ascii.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        
        # Add date prefix
        date_prefix = datetime.now().strftime('%Y%m%d')
        
        return f"{date_prefix}-{slug[:50].rstrip('-')}"
    
    def _load_existing_data(self, file_path: Path) -> Dict:
        """Load existing articles data or create new structure."""
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Error loading existing data: {e}")
        
        return {
            'articles': [],
            'categories': {},
            'daily_index': {},
            'last_updated': '',
            'total_articles': 0
        }
    
    def _update_categories_index(self, articles: List[Dict]) -> Dict:
        """Update categories index."""
        categories = {}
        
        for article in articles:
            category = article.get('category', 'other')
            if category not in categories:
                categories[category] = []
            
            categories[category].append({
                'slug': article.get('slug'),
                'title': article.get('title'),
                'date': article.get('published_date')
            })
        
        # Sort each category by date
        for category in categories:
            categories[category].sort(
                key=lambda x: x.get('date', ''), 
                reverse=True
            )
        
        return categories
    
    def _update_daily_index(self, articles: List[Dict]) -> Dict:
        """Update daily index."""
        daily_index = {}
        
        for article in articles:
            date = article.get('published_date', '')
            if date:
                if date not in daily_index:
                    daily_index[date] = []
                
                daily_index[date].append({
                    'slug': article.get('slug'),
                    'title': article.get('title'),
                    'category': article.get('category')
                })
        
        return daily_index

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Psychology News Site Automation')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Collect command
    collect_parser = subparsers.add_parser('collect', help='Collect articles')
    collect_parser.add_argument('--date', required=True, help='Date to collect for (YYYY-MM-DD)')
    collect_parser.add_argument('--limit', type=int, default=10, help='Maximum articles to collect')
    collect_parser.add_argument('--output', required=True, help='Output JSON file')
    
    # Evaluate command
    evaluate_parser = subparsers.add_parser('evaluate', help='Evaluate article quality')
    evaluate_parser.add_argument('--input', required=True, help='Input JSON file')
    evaluate_parser.add_argument('--output', required=True, help='Output JSON file')
    evaluate_parser.add_argument('--threshold', type=int, default=70, help='Quality threshold')
    
    # Summarize command
    summarize_parser = subparsers.add_parser('summarize', help='Generate AI summaries')
    summarize_parser.add_argument('--input', required=True, help='Input JSON file')
    summarize_parser.add_argument('--output', required=True, help='Output JSON file')
    summarize_parser.add_argument('--max-articles', type=int, default=3, help='Maximum articles to summarize')
    
    # Update site command
    update_parser = subparsers.add_parser('update-site', help='Update site data')
    update_parser.add_argument('--articles', required=True, help='Articles JSON file')
    update_parser.add_argument('--site-dir', required=True, help='Site directory')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    automation = PsychologyNewsAutomation()
    
    try:
        if args.command == 'collect':
            articles = await automation.collect_articles(args.date, args.limit)
            
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump({'articles': articles}, f, ensure_ascii=False, indent=2)
            
            print(f"Collected {len(articles)} articles to {args.output}")
        
        elif args.command == 'evaluate':
            with open(args.input, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            articles = data.get('articles', [])
            evaluated = automation.evaluate_articles(articles, args.threshold)
            
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump({'articles': evaluated}, f, ensure_ascii=False, indent=2)
            
            print(f"Evaluated {len(evaluated)} articles to {args.output}")
        
        elif args.command == 'summarize':
            with open(args.input, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            articles = data.get('articles', [])
            summarized = await automation.summarize_articles(articles, args.max_articles)
            
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump({'articles': summarized}, f, ensure_ascii=False, indent=2)
            
            print(f"Summarized {len(summarized)} articles to {args.output}")
        
        elif args.command == 'update-site':
            with open(args.articles, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            articles = data.get('articles', [])
            automation.update_site_data(articles, args.site_dir)
            
            print(f"Updated site data with {len(articles)} articles")
    
    except Exception as e:
        logging.error(f"Error in {args.command}: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())