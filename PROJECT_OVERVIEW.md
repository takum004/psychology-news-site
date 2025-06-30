# 心理学ニュースサイト プロジェクト概要

## 🎯 プロジェクトの目的

エビデンスベースの心理学研究を一般の人々にわかりやすく届ける、完全自動化されたニュースサイトを構築しています。

## 🏗️ システム構成

### 1. バックエンド（Python）
**場所**: `/src/`

#### データ収集モジュール
- **RSS Collector** (`/src/collectors/rss_collector.py`)
  - PsyPost、Psychology Todayなどから記事を収集
  - 心理学関連キーワードでフィルタリング
  
- **PubMed Collector** (`/src/collectors/pubmed_collector.py`)
  - 最新の学術論文を検索・収集
  - API経由で論文のメタデータを取得

#### 品質評価システム（パレオさんスタイル）
**ファイル**: `/src/evaluator/quality_evaluator.py`

評価基準：
- 研究デザインの質（メタアナリシス、RCT、コホート研究など）
- サンプルサイズ
- 効果量（Cohen's d、相関係数など）
- 実践可能性
- 安全性
- 最新性

スコアリング：
- 100点満点で評価
- 70点以上の記事のみサイトに掲載
- エビデンスレベル：Gold/Silver/Bronze

#### メイン処理
**ファイル**: `/src/main_nosummary.py`
- 記事収集 → 品質評価 → サイトデータ更新の一連の処理を実行
- OpenAI APIキーなしで動作（要約なしバージョン）

### 2. フロントエンド（Astro + React）
**場所**: `/site/`

- **フレームワーク**: Astro（静的サイトジェネレーター）
- **UIライブラリ**: React
- **スタイリング**: Tailwind CSS
- **レスポンシブデザイン**: モバイル対応

主要ファイル：
- `/site/src/pages/index.astro` - トップページ
- `/site/src/components/ArticleCard.jsx` - 記事カードコンポーネント
- `/site/src/data/articles.json` - 記事データ

### 3. 自動化（GitHub Actions）
**場所**: `/.github/workflows/`

#### daily-update.yml（メインワークフロー）
毎日JST 5:00に実行：
1. RSS/PubMedから記事収集
2. 品質評価でフィルタリング
3. サイトデータ更新
4. GitHub Pagesへデプロイ

#### deploy-gh-pages.yml
- mainブランチへのプッシュ時に実行
- サイトをビルドしてGitHub Pagesへデプロイ

#### test-and-validate.yml
- コード品質チェック
- Python/JavaScriptのテスト実行
- YAML構文検証

## 📊 現在の状況

### ✅ 完了済み
- Pythonバックエンドの実装
- RSS/PubMed収集機能
- 品質評価システム（パレオさんスタイル）
- Astroフロントエンドサイト
- GitHub Actions自動化
- GitHub Pagesデプロイ設定

### 🚧 進行中
- GitHub Actionsワークフローのデバッグ
- 初回デプロイの実行

### 📋 今後の予定
- OpenAI APIを使った要約機能の追加（オプション）
- カテゴリー別ページの追加
- 検索機能の実装
- メール配信機能

## 🌐 公開URL

**サイトURL**: https://takum004.github.io/psychology-news-site/

## 🛠️ 開発環境セットアップ

### 必要なもの
- Python 3.9以上
- Node.js 18以上
- Git

### セットアップ手順

```bash
# リポジトリのクローン
git clone https://github.com/takum004/psychology-news-site.git
cd psychology-news-site

# Pythonの依存関係インストール
pip install -r requirements.txt

# フロントエンドの依存関係インストール
cd site
npm install
```

### ローカルでの実行

```bash
# バックエンド（記事収集）
python -m src.main_nosummary collect --date 2024-07-01 --limit 10 --output data/articles.json

# フロントエンド（開発サーバー）
cd site
npm run dev
```

## 🔑 環境変数

必要な環境変数（GitHub Secretsに設定）：
- `PUBMED_API_KEY` - PubMed APIキー（オプション）
- `OPENAI_API_KEY` - OpenAI APIキー（要約機能使用時のみ）

## 📝 トラブルシューティング

### GitHub Actions失敗時
1. Actionsタブでエラーログを確認
2. `.github/workflows/`内の該当ワークフローを確認
3. 権限設定を確認（Settings → Actions → General）

### サイトが表示されない場合
1. GitHub Pages設定を確認（Settings → Pages）
2. Source: GitHub Actionsが選択されているか確認
3. デプロイワークフローが成功しているか確認

## 👥 貢献者

- 開発: Claude Code & takum004
- インスピレーション: パレオな男（鈴木祐）スタイルの科学的評価方法

---

最終更新: 2024年7月1日