import pdb
import traceback
import urllib.parse
from bs4 import BeautifulSoup
import requests
import os


class ReqPubmedID:
    def __init__(self):
        pass

    def _fetch(self, term, field, retmax):
        DEFAULT_PUBMED_API_KEY = os.environ.get('PUBMED_API_KEY')

        headers = {
            'User-Agent': 'Mozilla/5.0',
        }
        
        params = {
            'db': 'pubmed',
            'term': f'{term}[{field}]',
            'retmax': retmax,
            'retmode': 'xml',
            'api_key': DEFAULT_PUBMED_API_KEY
        }
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
        search_url += urllib.parse.urlencode(params)
        response = requests.get(search_url, headers = headers)
        soup = BeautifulSoup(response.text, "xml")
        result_ids:list[str] = [id.text for id in soup.select('IdList Id')]
        return result_ids


    def run(self, term, field="Title/Abstract", retmax=100):
        try:
            result_ids = self._fetch(term, field, retmax)
        except Exception:
            traceback.print_exc()
        return result_ids
    
class ReqPubmedFull:
    def __init__(self):
        pass
    
    def _fetch(self, result_ids:list[str]) -> list[dict]:
        DEFAULT_PUBMED_API_KEY = os.environ.get('PUBMED_API_KEY')

        headers = {
            'User-Agent': 'Mozilla/5.0',
        }
        
        params = {
            'db': 'pubmed',
            'id': ','.join(result_ids),
            'retmode': 'xml',
            'api_key': DEFAULT_PUBMED_API_KEY,
        }
        
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
        search_url += urllib.parse.urlencode(params)
        
        response = requests.get(search_url, headers = headers)
        soup = BeautifulSoup(response.text, "xml")

        pubmed_data = []
        for article in soup.select('PubmedArticle'):
            title = article.find('ArticleTitle').text
            abstract = ' '.join([node.text for node in article.select('AbstractText')])
            data = {'title': title, 'abstract': abstract, "doi": None, "pubmed_id": None, "pmcid": None, "mesh_terms": []}
            
            # Extract IDs and mesh terms
            mesh_terms = self._extract_meshterms(article)
            data['mesh_terms'] = mesh_terms
            ids = self._extract_ids(article)
            data.update(ids)

            pubmed_data.append(data)

        return pubmed_data

    def _extract_meshterms(selff, article):
        mesh_terms_outputs = []
        mesh_terms = article.find("MeshHeadingList")
        if mesh_terms is not None:
            mesh_terms = mesh_terms.select("MeshHeading")
        if mesh_terms is not None:
            for mesh_term in mesh_terms:
                mesh_terms_outputs.append(mesh_term.text)
        return mesh_terms_outputs

    def _extract_ids(self, article):
        data = {"doi": None, "pubmed_id": None, "pmcid": None}
        article_ids = article.find("ArticleIdList")
        if article_ids is not None:
            article_ids = article_ids.select("ArticleId")
            for article_id in article_ids:
                if article_id['IdType'] == "doi":
                    data['doi'] = article_id.text
                if article_id['IdType'] == "pubmed":
                    data['pubmed_id'] = article_id.text
                if article_id['IdType'] == "pmc":
                    data['pmcid'] = article_id.text
        return data

    def run(self, result_ids:list[str]) -> list[dict]:
        try:
            pubmed_data = self._fetch(result_ids)
        except Exception:
            traceback.print_exc()
        return pubmed_data