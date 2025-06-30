"""
OpenAI API client for generating structured summaries.
"""

import json
import asyncio
import logging
from typing import Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import openai
from .prompt_builder import PromptBuilder

class OpenAISummarizer:
    """OpenAI APIを使用した要約生成"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model
        self.prompt_builder = PromptBuilder()
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """ロガーの設定"""
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def summarize_article(
        self, 
        article: Dict, 
        evaluation: Dict
    ) -> Optional[Dict]:
        """記事の要約生成"""
        try:
            prompt = self.prompt_builder.build_article_prompt(
                article, evaluation
            )
            
            self.logger.info(f"Summarizing article: {article.get('title', 'Unknown')[:50]}...")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PromptBuilder.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            
            # レスポンスの解析
            content = response.choices[0].message.content
            summary_data = json.loads(content)
            
            # 検証
            if self._validate_summary(summary_data):
                self.logger.info("Summary generated successfully")
                return summary_data
            else:
                self.logger.warning("Summary validation failed")
                return None
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Summarization failed: {e}")
            return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def generate_weekly_review(
        self, 
        articles: List[Dict]
    ) -> Optional[Dict]:
        """週次統合レビューの生成"""
        try:
            if not articles:
                return None
            
            prompt = self.prompt_builder.build_weekly_review_prompt(articles)
            
            self.logger.info(f"Generating weekly review for {len(articles)} articles")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PromptBuilder.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            review_data = json.loads(content)
            
            if self._validate_weekly_review(review_data):
                self.logger.info("Weekly review generated successfully")
                return review_data
            else:
                self.logger.warning("Weekly review validation failed")
                return None
                
        except Exception as e:
            self.logger.error(f"Weekly review generation failed: {e}")
            return None
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=30)
    )
    async def categorize_article(self, article: Dict) -> Optional[str]:
        """記事のカテゴリ分類"""
        try:
            prompt = self.prompt_builder.build_categorization_prompt(article)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは心理学記事の分類専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            categorization = json.loads(content)
            
            category = categorization.get('primary_category')
            confidence = categorization.get('confidence', 0.0)
            
            # 信頼度が低い場合はデフォルトカテゴリ
            if confidence < 0.7:
                return 'motivation'  # デフォルト
            
            return category
            
        except Exception as e:
            self.logger.error(f"Categorization failed: {e}")
            return 'motivation'  # デフォルト
    
    async def batch_summarize(
        self, 
        article_evaluation_pairs: List[tuple]
    ) -> List[Dict]:
        """複数記事の並列要約"""
        tasks = []
        
        for article, evaluation in article_evaluation_pairs:
            task = self.summarize_article(article, evaluation)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_summaries = []
        for result in results:
            if isinstance(result, dict):
                valid_summaries.append(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Batch summarization error: {result}")
        
        return valid_summaries
    
    def _validate_summary(self, summary: Dict) -> bool:
        """要約データの検証"""
        required_fields = [
            'title', 'subtitle', 'summary_points',
            'research_details', 'protocol', 'evidence_level'
        ]
        
        # 必須フィールドの確認
        if not all(field in summary for field in required_fields):
            self.logger.warning(f"Missing required fields: {required_fields}")
            return False
        
        # summary_pointsが配列で3つ以上の要素があるか
        if not isinstance(summary['summary_points'], list) or len(summary['summary_points']) < 3:
            self.logger.warning("Invalid summary_points")
            return False
        
        # protocolが配列で少なくとも1つの要素があるか
        if not isinstance(summary['protocol'], list) or len(summary['protocol']) < 1:
            self.logger.warning("Invalid protocol")
            return False
        
        # evidence_levelが有効な値か
        valid_levels = ['gold', 'silver', 'bronze']
        if summary['evidence_level'] not in valid_levels:
            self.logger.warning(f"Invalid evidence_level: {summary['evidence_level']}")
            return False
        
        return True
    
    def _validate_weekly_review(self, review: Dict) -> bool:
        """週次レビューデータの検証"""
        required_fields = [
            'weekly_theme', 'integrated_findings', 
            'practical_synthesis', 'meta_analysis'
        ]
        
        if not all(field in review for field in required_fields):
            self.logger.warning(f"Missing required fields in weekly review")
            return False
        
        # integrated_findingsが配列か
        if not isinstance(review['integrated_findings'], list):
            self.logger.warning("Invalid integrated_findings")
            return False
        
        return True
    
    def estimate_tokens(self, text: str) -> int:
        """トークン数の概算"""
        # 簡易的な推定（日本語では1文字≈1.5トークン）
        return int(len(text) * 1.5)
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """API利用料金の概算（USD）"""
        # GPT-4o-mini の料金（2024年時点）
        input_cost_per_1k = 0.00015  # $0.15 per 1K tokens
        output_cost_per_1k = 0.0006  # $0.60 per 1K tokens
        
        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        
        return input_cost + output_cost