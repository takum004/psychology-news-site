"""
Prompt builder for creating structured prompts for AI summarization.
"""

from typing import Dict, List
import json

class PromptBuilder:
    """構造化プロンプトの構築"""
    
    SYSTEM_PROMPT = """あなたは科学的根拠を重視する心理学の専門家です。
パレオダイエットの鈴木祐氏のような、エビデンスと数値を重視したスタイルで記事を要約してください。

重要な原則：
1. 必ず具体的な数値（被験者数、効果量、信頼区間等）を含める
2. 研究の限界や個人差についても正直に記述する
3. 実践方法は具体的かつ段階的に説明する
4. 専門用語は避け、一般の人にも分かりやすく説明する
5. 「～の可能性がある」「～と考えられる」など曖昧な表現は避ける
6. 数値は必ず根拠を示す

パレオスタイルの特徴：
- エビデンスレベルを明確に表示
- 効果量や被験者数を必ず記載
- 効果が出ない人の割合も明記
- コストパフォーマンスを考慮
- 批判的な視点を保つ"""

    def build_article_prompt(self, article: Dict, evaluation: Dict) -> str:
        """記事要約用のプロンプト構築"""
        
        # 記事の基本情報を取得
        title = article.get('title', '')
        abstract = article.get('abstract', article.get('summary', ''))
        source = article.get('source', '')
        
        # 評価情報
        study_type = evaluation.get('study_type', '不明')
        sample_size = evaluation.get('sample_size', '不明')
        effect_size = evaluation.get('effect_size', '不明')
        evidence_level = evaluation.get('evidence_level', 'bronze')
        
        return f"""
以下の研究を、パレオスタイルで要約してください。

【研究情報】
タイトル: {title}
ソース: {source}
研究タイプ: {study_type}
サンプルサイズ: {sample_size}
効果量: {effect_size}
エビデンスレベル: {evidence_level}

【研究内容】
{abstract}

【要約フォーマット】
以下のJSON形式で出力してください：

{{
  "title": "数値を含むキャッチーなタイトル（例：記憶力が23%向上する○○法）",
  "subtitle": "具体的な研究結果を含むサブタイトル",
  "summary_points": [
    "ポイント1（必ず数値を含める）",
    "ポイント2（必ず数値を含める）", 
    "ポイント3（必ず数値を含める）"
  ],
  "evidence_level": "{evidence_level}",
  "research_details": {{
    "sample_size": {sample_size if isinstance(sample_size, int) else 'null'},
    "effect_size": {effect_size if isinstance(effect_size, (int, float)) else 'null'},
    "confidence_interval": [下限, 上限] または null,
    "p_value": p値 または null,
    "study_duration": "研究期間",
    "study_type": "{study_type}"
  }},
  "practical_numbers": {{
    "time_to_effect": "効果が出るまでの期間（例：2週間）",
    "success_rate": "成功率（例：68%）",
    "individual_variance": "個人差の程度（例：効果に3倍の差）",
    "cost_estimate": "必要なコスト（例：月500円）"
  }},
  "protocol": [
    {{
      "step": 1,
      "action": "具体的なアクション（例：朝起きたら5分間瞑想）",
      "duration": "所要時間（例：5分）",
      "frequency": "頻度（例：毎日）",
      "difficulty": 1
    }},
    {{
      "step": 2,
      "action": "次のステップ",
      "duration": "所要時間",
      "frequency": "頻度",
      "difficulty": 2
    }}
  ],
  "warnings": [
    "効果が出ない人の特徴（例：○○の人には効果なし）",
    "注意点や副作用（例：やりすぎると逆効果）"
  ],
  "mechanism": "なぜ効果があるのかの簡単な説明（専門用語避ける）",
  "paleo_style_notes": {{
    "cost_benefit": "時間・費用対効果の分析",
    "evidence_quality": "エビデンスの強さと限界",
    "practical_barriers": "実践する上での障壁"
  }},
  "references": [
    {{
      "authors": "著者名",
      "year": 発行年,
      "journal": "雑誌名",
      "doi": "DOI"
    }}
  ]
}}

重要：
- すべての数値は研究データに基づいて記載
- 効果が出ない人の割合も必ず含める
- 実践プロトコルは今日から始められる内容
- コストや時間も現実的に算出
- 誇張や憶測は一切含めない
"""

    def build_weekly_review_prompt(self, articles: List[Dict]) -> str:
        """週次統合レビュー用のプロンプト構築"""
        articles_summary = "\n".join([
            f"- {a.get('title', 'タイトル不明')} (効果量: {a.get('effect_size', '不明')}, n={a.get('sample_size', '不明')})"
            for a in articles
        ])
        
        return f"""
今週の心理学研究をメタ分析的に統合してください。

【今週の研究一覧】
{articles_summary}

【統合分析の指示】
パレオスタイルで以下の観点から分析してください：

1. 数値の統合分析
   - 各研究の効果量を比較
   - サンプルサイズの加重平均
   - 統合効果量の算出

2. 矛盾の解決
   - 異なる結果の統合的解釈
   - 個人差要因の特定
   - 条件による効果の違い

3. 実践的統合
   - 優先順位付けされた実践リスト
   - 組み合わせ効果の検討
   - リスク・ベネフィット分析

【出力フォーマット】
{{
  "weekly_theme": "今週のテーマ",
  "meta_analysis": {{
    "total_participants": "統合参加者数",
    "average_effect_size": "統合効果量",
    "confidence_interval": [下限, 上限],
    "heterogeneity": "研究間の異質性"
  }},
  "integrated_findings": [
    {{
      "finding": "統合的発見1",
      "supporting_studies": ["研究1", "研究2"],
      "combined_effect": "統合効果量",
      "confidence": "確信度（高/中/低）"
    }}
  ],
  "practical_synthesis": {{
    "priority_recommendations": [
      "最優先実践（効果量・コスパ・安全性を考慮）",
      "次の実践",
      "長期的実践"
    ],
    "implementation_schedule": {{
      "week1": "まず始めること",
      "week2-4": "習慣化する内容",
      "month2-3": "長期的取り組み"
    }},
    "expected_timeline": "全体の実践期間と効果出現時期"
  }},
  "contradictions_resolved": [
    {{
      "contradiction": "矛盾点",
      "possible_explanation": "考えられる説明",
      "practical_implication": "実践への示唆"
    }}
  ],
  "paleo_analysis": {{
    "cost_effectiveness": "コストパフォーマンス分析",
    "individual_factors": {{
      "high_responders": "効果が高い人の特徴",
      "low_responders": "効果が低い人の特徴",
      "optimal_conditions": "最適な実践条件"
    }},
    "critical_evaluation": "研究の限界と注意点"
  }}
}}
"""

    def build_categorization_prompt(self, article: Dict) -> str:
        """記事分類用のプロンプト"""
        title = article.get('title', '')
        abstract = article.get('abstract', article.get('summary', ''))
        
        return f"""
以下の記事を適切なカテゴリに分類してください。

記事タイトル: {title}
要約: {abstract}

カテゴリ選択肢：
1. motivation - モチベーション、目標設定、やる気
2. communication - コミュニケーション、対人スキル
3. stress - ストレス管理、リラクゼーション
4. productivity - 生産性、習慣形成、時間管理
5. relationships - 人間関係、信頼、絆

以下のJSON形式で回答してください：
{{
  "primary_category": "最も適切なカテゴリ",
  "confidence": "信頼度（0.0-1.0）",
  "reasoning": "分類理由"
}}
"""