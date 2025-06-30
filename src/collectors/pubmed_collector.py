"""
PubMed API collector for gathering academic psychology research papers.
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .base_collector import BaseCollector

class PubMedCollector(BaseCollector):
    """PubMed APIからの論文収集"""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.api_key = config.get('pubmed_api_key')
        self.email = config.get('email', 'user@example.com')
    
    async def collect(self, query: str = "psychology", limit: int = 10) -> List[Dict]:
        """PubMedから論文を収集"""
        try:
            # 検索クエリの構築
            search_query = self._build_query(query)
            
            # ID検索
            ids = await self._search_ids(search_query, limit)
            if not ids:
                return []
            
            # 詳細取得
            articles = await self._fetch_details(ids)
            
            # 検証とフィルタリング
            valid_articles = []
            for article in articles:
                if self.validate_article(article):
                    valid_articles.append(article)
            
            return valid_articles
            
        except Exception as e:
            self.logger.error(f"PubMed collection error: {e}")
            return []
    
    def _build_query(self, base_query: str) -> str:
        """検索クエリの構築"""
        # 心理学関連の検索語を構築
        psychology_terms = [
            "psychology[MeSH]",
            "psychological phenomena[MeSH]",
            "behavior[MeSH]",
            "mental health[MeSH]"
        ]
        
        # 研究タイプのフィルタ
        study_types = [
            "randomized controlled trial[PT]",
            "meta-analysis[PT]",
            "systematic review[PT]",
            "clinical trial[PT]"
        ]
        
        # 期間指定（過去2年）
        date_filter = f"(\"{(datetime.now() - timedelta(days=730)).strftime('%Y/%m/%d')}\"[PDAT] : \"3000\"[PDAT])"
        
        # クエリの組み立て
        if base_query and base_query != "psychology":
            main_query = f"({base_query})"
        else:
            main_query = f"({' OR '.join(psychology_terms)})"
        
        study_filter = f"({' OR '.join(study_types)})"
        
        final_query = f"{main_query} AND {study_filter} AND {date_filter} AND English[lang]"
        
        return final_query
    
    async def _search_ids(self, query: str, limit: int) -> List[str]:
        """論文IDの検索"""
        params = {
            'db': 'pubmed',
            'term': query,
            'retmax': limit,
            'sort': 'relevance',
            'retmode': 'xml'
        }
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}esearch.fcgi"
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        content = await response.text()
                        return self._parse_search_results(content)
                    else:
                        self.logger.error(f"Search failed: {response.status}")
                        return []
        
        except Exception as e:
            self.logger.error(f"Search error: {e}")
            return []
    
    def _parse_search_results(self, xml_content: str) -> List[str]:
        """検索結果XMLからIDを抽出"""
        try:
            root = ET.fromstring(xml_content)
            ids = []
            
            for id_elem in root.findall('.//Id'):
                if id_elem.text:
                    ids.append(id_elem.text)
            
            return ids
        
        except Exception as e:
            self.logger.error(f"Error parsing search results: {e}")
            return []
    
    async def _fetch_details(self, ids: List[str]) -> List[Dict]:
        """論文詳細の取得"""
        if not ids:
            return []
        
        params = {
            'db': 'pubmed',
            'id': ','.join(ids),
            'retmode': 'xml',
            'rettype': 'abstract'
        }
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}efetch.fcgi"
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        content = await response.text()
                        return self._parse_article_details(content)
                    else:
                        self.logger.error(f"Fetch failed: {response.status}")
                        return []
        
        except Exception as e:
            self.logger.error(f"Fetch error: {e}")
            return []
    
    def _parse_article_details(self, xml_content: str) -> List[Dict]:
        """論文詳細XMLの解析"""
        try:
            root = ET.fromstring(xml_content)
            articles = []
            
            for article_elem in root.findall('.//PubmedArticle'):
                article = self._parse_single_article(article_elem)
                if article:
                    articles.append(article)
            
            return articles
        
        except Exception as e:
            self.logger.error(f"Error parsing article details: {e}")
            return []
    
    def _parse_single_article(self, article_elem) -> Optional[Dict]:
        """単一論文の解析"""
        try:
            # 基本情報の取得
            medline_citation = article_elem.find('.//MedlineCitation')
            if medline_citation is None:
                return None
            
            pmid_elem = medline_citation.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else None
            
            article_elem_inner = medline_citation.find('.//Article')
            if article_elem_inner is None:
                return None
            
            # タイトル
            title_elem = article_elem_inner.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else ""
            
            # 要約
            abstract_text = ""
            abstract_elem = article_elem_inner.find('.//Abstract')
            if abstract_elem is not None:
                abstract_texts = abstract_elem.findall('.//AbstractText')
                abstract_parts = []
                for abs_text in abstract_texts:
                    if abs_text.text:
                        label = abs_text.get('Label', '')
                        if label:
                            abstract_parts.append(f"{label}: {abs_text.text}")
                        else:
                            abstract_parts.append(abs_text.text)
                abstract_text = " ".join(abstract_parts)
            
            # 著者
            authors = []
            author_list = article_elem_inner.find('.//AuthorList')
            if author_list is not None:
                for author in author_list.findall('.//Author'):
                    last_name = author.find('.//LastName')
                    first_name = author.find('.//ForeName')
                    if last_name is not None and first_name is not None:
                        authors.append(f"{first_name.text} {last_name.text}")
            
            # 雑誌情報
            journal_elem = article_elem_inner.find('.//Journal')
            journal_title = ""
            if journal_elem is not None:
                title_elem = journal_elem.find('.//Title')
                if title_elem is not None:
                    journal_title = title_elem.text
            
            # 発行日
            pub_date = self._extract_publication_date(article_elem_inner)
            
            # DOI
            doi = self._extract_doi(article_elem_inner)
            
            # 研究タイプ
            publication_types = []
            pub_type_list = article_elem_inner.find('.//PublicationTypeList')
            if pub_type_list is not None:
                for pub_type in pub_type_list.findall('.//PublicationType'):
                    if pub_type.text:
                        publication_types.append(pub_type.text)
            
            # MeSH terms
            mesh_terms = self._extract_mesh_terms(medline_citation)
            
            return {
                'source': 'pubmed',
                'pmid': pmid,
                'doi': doi,
                'title': self.sanitize_text(title),
                'abstract': self.sanitize_text(abstract_text),
                'authors': authors,
                'journal': journal_title,
                'published_date': pub_date,
                'publication_types': publication_types,
                'mesh_terms': mesh_terms,
                'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                'collected_at': datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Error parsing single article: {e}")
            return None
    
    def _extract_publication_date(self, article_elem) -> str:
        """発行日の抽出"""
        try:
            # ArticleDate を優先
            article_date = article_elem.find('.//ArticleDate')
            if article_date is not None:
                year = article_date.find('.//Year')
                month = article_date.find('.//Month')
                day = article_date.find('.//Day')
                
                if year is not None:
                    year_text = year.text
                    month_text = month.text if month is not None else "01"
                    day_text = day.text if day is not None else "01"
                    
                    return f"{year_text}-{month_text.zfill(2)}-{day_text.zfill(2)}"
            
            # Journal Issue の PubDate
            journal = article_elem.find('.//Journal')
            if journal is not None:
                pub_date = journal.find('.//PubDate')
                if pub_date is not None:
                    year = pub_date.find('.//Year')
                    if year is not None:
                        return f"{year.text}-01-01"
            
            return datetime.now().strftime('%Y-%m-%d')
        
        except:
            return datetime.now().strftime('%Y-%m-%d')
    
    def _extract_doi(self, article_elem) -> Optional[str]:
        """DOIの抽出"""
        try:
            article_id_list = article_elem.find('.//ArticleIdList')
            if article_id_list is not None:
                for article_id in article_id_list.findall('.//ArticleId'):
                    if article_id.get('IdType') == 'doi':
                        return article_id.text
            return None
        except:
            return None
    
    def _extract_mesh_terms(self, medline_citation) -> List[str]:
        """MeSH用語の抽出"""
        try:
            mesh_terms = []
            mesh_heading_list = medline_citation.find('.//MeshHeadingList')
            if mesh_heading_list is not None:
                for mesh_heading in mesh_heading_list.findall('.//MeshHeading'):
                    descriptor = mesh_heading.find('.//DescriptorName')
                    if descriptor is not None and descriptor.text:
                        mesh_terms.append(descriptor.text)
            return mesh_terms
        except:
            return []
    
    def parse_response(self, response: Dict) -> List[Dict]:
        """レスポンス解析（このクラスでは直接XMLを処理）"""
        return []