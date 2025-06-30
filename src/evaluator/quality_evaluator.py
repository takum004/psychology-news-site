"""
Quality evaluation engine for assessing research articles.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from datetime import datetime

@dataclass
class EvaluationResult:
    """評価結果のデータクラス"""
    total_score: int
    breakdown: Dict[str, int]
    evidence_level: str
    recommendation: str
    details: Dict
    study_type: str
    sample_size: Optional[int]
    effect_size: Optional[float]

class QualityEvaluator:
    """記事の品質評価エンジン"""
    
    # 研究デザインのスコアリング
    STUDY_DESIGN_SCORES = {
        'meta-analysis': 40,
        'systematic review': 35,
        'rct': 30,
        'cohort study': 20,
        'case-control': 15,
        'cross-sectional': 10,
        'case report': 5,
        'review': 25,
        'observational': 12
    }
    
    # 効果量の閾値
    EFFECT_SIZE_THRESHOLDS = {
        'large': (0.8, 20),
        'medium': (0.5, 15),
        'small': (0.2, 10),
        'trivial': (0, 5)
    }
    
    def evaluate(self, article: Dict) -> EvaluationResult:
        """記事の総合評価"""
        # 各項目の評価
        study_quality_score = self._evaluate_study_quality(article)
        effect_size_score = self._evaluate_effect_size(article)
        applicability_score = self._evaluate_applicability(article)
        safety_score = self._evaluate_safety(article)
        recency_score = self._evaluate_recency(article)
        
        scores = {
            'study_quality': study_quality_score,
            'effect_size': effect_size_score,
            'practical_applicability': applicability_score,
            'safety': safety_score,
            'recency': recency_score
        }
        
        total_score = sum(scores.values())
        evidence_level = self._determine_evidence_level(article, scores)
        study_type = self._identify_study_type(article)
        sample_size = self._extract_sample_size(article)
        effect_size = self._extract_effect_size(article)
        
        return EvaluationResult(
            total_score=total_score,
            breakdown=scores,
            evidence_level=evidence_level,
            recommendation=self._get_recommendation(total_score),
            details=self._extract_key_metrics(article),
            study_type=study_type,
            sample_size=sample_size,
            effect_size=effect_size
        )
    
    def _evaluate_study_quality(self, article: Dict) -> int:
        """研究の質の評価"""
        # 研究デザインの特定
        study_type = self._identify_study_type(article)
        base_score = self.STUDY_DESIGN_SCORES.get(study_type, 5)
        
        # 追加要因による調整
        adjustments = 0
        
        # サンプルサイズによる調整
        sample_size = self._extract_sample_size(article)
        if sample_size:
            if sample_size >= 10000:
                adjustments += 5
            elif sample_size >= 1000:
                adjustments += 3
            elif sample_size >= 100:
                adjustments += 1
        
        # 統計的検出力の考慮
        if self._has_power_analysis(article):
            adjustments += 2
        
        # 雑誌の質による調整
        if self._is_high_impact_journal(article):
            adjustments += 3
        
        return min(base_score + adjustments, 40)
    
    def _identify_study_type(self, article: Dict) -> str:
        """研究タイプの特定"""
        text = f"{article.get('title', '')} {article.get('abstract', '')} {article.get('summary', '')}".lower()
        
        # PubMedの場合、publication_typesも使用
        pub_types = article.get('publication_types', [])
        pub_types_text = ' '.join(pub_types).lower()
        
        patterns = {
            'meta-analysis': r'meta-?analys[ie]s|systematic review and meta|meta analysis',
            'systematic review': r'systematic review|cochrane review',
            'rct': r'randomi[sz]ed controlled trial|rct|randomi[sz]ed trial|clinical trial',
            'cohort study': r'cohort study|prospective study|longitudinal study',
            'case-control': r'case-?control study',
            'cross-sectional': r'cross-?sectional|survey study',
            'case report': r'case report|case study',
            'review': r'review|narrative review'
        }
        
        # まずpublication typesをチェック
        for study_type, pattern in patterns.items():
            if re.search(pattern, pub_types_text):
                return study_type
        
        # 次にタイトルと要約をチェック
        for study_type, pattern in patterns.items():
            if re.search(pattern, text):
                return study_type
        
        return 'observational'
    
    def _extract_sample_size(self, article: Dict) -> Optional[int]:
        """サンプルサイズの抽出"""
        text = f"{article.get('abstract', '')} {article.get('summary', '')}"
        
        # 様々なパターンでサンプルサイズを検索
        patterns = [
            r'n\s*=\s*(\d+[,\d]*)',
            r'(\d+[,\d]*)\s*participants?',
            r'(\d+[,\d]*)\s*subjects?',
            r'sample size.*?(\d+[,\d]*)',
            r'total of\s*(\d+[,\d]*)',
            r'study included\s*(\d+[,\d]*)',
            r'recruited\s*(\d+[,\d]*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # カンマを除去して数値に変換
                size_str = match.group(1).replace(',', '')
                try:
                    size = int(size_str)
                    # 現実的な範囲チェック
                    if 10 <= size <= 10000000:
                        return size
                except ValueError:
                    continue
        
        return None
    
    def _evaluate_effect_size(self, article: Dict) -> int:
        """効果量の評価"""
        effect_size = self._extract_effect_size(article)
        
        if effect_size is None:
            # 効果量が明記されていない場合は低めのスコア
            return 5
        
        # 効果量の大きさに基づくスコアリング
        abs_effect = abs(effect_size)
        for threshold, (min_d, score) in self.EFFECT_SIZE_THRESHOLDS.items():
            if abs_effect >= min_d:
                return score
        
        return 5
    
    def _extract_effect_size(self, article: Dict) -> Optional[float]:
        """効果量の抽出（Cohen's d, Hedge's g, r, OR等）"""
        text = f"{article.get('abstract', '')} {article.get('summary', '')}"
        
        # Cohen's d または Hedge's g
        d_patterns = [
            r"(?:cohen'?s?\s*d|hedge'?s?\s*g)\s*=\s*([-]?\d+\.?\d*)",
            r"effect size.*?d\s*=\s*([-]?\d+\.?\d*)",
            r"\bd\s*=\s*([-]?\d+\.?\d*)"
        ]
        
        for pattern in d_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        # 相関係数 r
        r_pattern = r"r\s*=\s*([-]?\d+\.?\d*)"
        match = re.search(r_pattern, text)
        if match:
            try:
                r = float(match.group(1))
                if -1 <= r <= 1:  # 有効な相関係数の範囲
                    # r を Cohen's d に変換
                    if abs(r) < 0.99:
                        return 2 * r / np.sqrt(1 - r**2)
            except (ValueError, ZeroDivisionError):
                pass
        
        # オッズ比
        or_pattern = r"odds ratio.*?([\d.]+)"
        match = re.search(or_pattern, text, re.IGNORECASE)
        if match:
            try:
                or_value = float(match.group(1))
                if or_value > 0:
                    # OR を Cohen's d に変換（近似）
                    return np.log(or_value) * np.sqrt(3) / np.pi
            except ValueError:
                pass
        
        return None
    
    def _evaluate_applicability(self, article: Dict) -> int:
        """実践可能性の評価"""
        score = 0
        text = f"{article.get('title', '')} {article.get('abstract', '')} {article.get('summary', '')}".lower()
        
        # 実践的要素のチェック
        practical_indicators = {
            'immediate': ['immediate', 'instant', 'quick', 'simple', 'easy'],
            'accessible': ['accessible', 'free', 'no cost', 'low cost'],
            'specific': ['protocol', 'procedure', 'step-by-step', 'guide', 'method'],
            'measurable': ['measure', 'assess', 'evaluate', 'track', 'monitor']
        }
        
        for category, keywords in practical_indicators.items():
            if any(keyword in text for keyword in keywords):
                score += 5
        
        # 実践の障壁チェック（減点）
        barriers = ['expensive', 'complex', 'professional only', 'clinical setting', 'specialized']
        barrier_count = sum(1 for barrier in barriers if barrier in text)
        score -= barrier_count * 3
        
        # 介入研究への加点
        if any(term in text for term in ['intervention', 'treatment', 'therapy', 'training']):
            score += 3
        
        return max(0, min(score, 20))
    
    def _evaluate_safety(self, article: Dict) -> int:
        """安全性の評価"""
        text = f"{article.get('abstract', '')} {article.get('summary', '')}".lower()
        
        # 安全性に関する記述
        safe_terms = ['safe', 'no adverse', 'well-tolerated', 'no side effects', 'minimal risk']
        if any(term in text for term in safe_terms):
            return 10
        
        # リスクに関する記述
        risk_terms = ['risk', 'adverse', 'caution', 'contraindication', 'side effect']
        if any(term in text for term in risk_terms):
            return 5
        
        # 記述なし（デフォルト）
        return 7
    
    def _evaluate_recency(self, article: Dict) -> int:
        """最新性の評価"""
        try:
            pub_date_str = article.get('published_date')
            if not pub_date_str:
                return 5  # デフォルト
            
            pub_date = datetime.strptime(pub_date_str, '%Y-%m-%d')
            days_old = (datetime.now() - pub_date).days
            
            if days_old <= 365:
                return 10
            elif days_old <= 1095:  # 3年
                return 7
            elif days_old <= 1825:  # 5年
                return 5
            else:
                return 3
        except:
            return 5  # デフォルト
    
    def _has_power_analysis(self, article: Dict) -> bool:
        """統計的検出力解析の有無"""
        text = f"{article.get('abstract', '')} {article.get('summary', '')}".lower()
        
        # 否定的な文脈での言及は除外
        negative_patterns = ['no power analysis', 'without power analysis', 'lacked power analysis']
        if any(pattern in text for pattern in negative_patterns):
            return False
        
        power_terms = ['power analysis', 'statistical power', 'power calculation', 'sample size calculation']
        return any(term in text for term in power_terms)
    
    def _is_high_impact_journal(self, article: Dict) -> bool:
        """高インパクト雑誌かどうか"""
        journal = article.get('journal', '').lower()
        high_impact_journals = [
            'nature', 'science', 'cell', 'lancet', 'new england journal',
            'psychological science', 'journal of personality and social psychology',
            'psychological bulletin', 'annual review'
        ]
        return any(journal_name in journal for journal_name in high_impact_journals)
    
    def _determine_evidence_level(self, article: Dict, scores: Dict) -> str:
        """エビデンスレベルの決定"""
        total_score = sum(scores.values())
        study_type = self._identify_study_type(article)
        
        # 高品質な研究デザインかつ高スコア
        if study_type in ['meta-analysis', 'systematic review'] and total_score >= 80:
            return 'gold'
        elif study_type == 'rct' and total_score >= 75:
            return 'gold'
        elif total_score >= 70:
            return 'silver'
        else:
            return 'bronze'
    
    def _get_recommendation(self, total_score: int) -> str:
        """推奨度の決定"""
        if total_score >= 80:
            return "強く推奨 - 高品質なエビデンス"
        elif total_score >= 70:
            return "推奨 - 十分なエビデンス"
        elif total_score >= 60:
            return "条件付き推奨 - 限定的なエビデンス"
        else:
            return "推奨しない - 不十分なエビデンス"
    
    def _extract_key_metrics(self, article: Dict) -> Dict:
        """主要な指標の抽出"""
        text = f"{article.get('abstract', '')} {article.get('summary', '')}"
        
        # p値の抽出
        p_value = None
        p_patterns = [r'p\s*[<>=]\s*([\d.]+)', r'p\s*=\s*([\d.]+)']
        for pattern in p_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    p_value = float(match.group(1))
                    break
                except ValueError:
                    continue
        
        # 信頼区間の抽出
        ci_pattern = r'(\d+)%?\s*(?:confidence interval|ci).*?([\d.-]+).*?([\d.-]+)'
        ci_match = re.search(ci_pattern, text, re.IGNORECASE)
        confidence_interval = None
        if ci_match:
            try:
                ci_lower = float(ci_match.group(2))
                ci_upper = float(ci_match.group(3))
                confidence_interval = [ci_lower, ci_upper]
            except ValueError:
                pass
        
        return {
            'p_value': p_value,
            'confidence_interval': confidence_interval,
            'study_duration': self._extract_study_duration(text),
            'follow_up_period': self._extract_follow_up(text)
        }
    
    def _extract_study_duration(self, text: str) -> Optional[str]:
        """研究期間の抽出"""
        duration_patterns = [
            r'(\d+)\s*(?:week|month|year)s?\s*(?:study|trial|follow)',
            r'over\s*(\d+)\s*(?:week|month|year)s?',
            r'during\s*(\d+)\s*(?:week|month|year)s?'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_follow_up(self, text: str) -> Optional[str]:
        """フォローアップ期間の抽出"""
        followup_patterns = [
            r'follow-?up.*?(\d+)\s*(?:week|month|year)s?',
            r'(\d+)\s*(?:week|month|year)s?\s*follow-?up'
        ]
        
        for pattern in followup_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None