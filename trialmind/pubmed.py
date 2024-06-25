import pdb
import traceback
import urllib.parse
import pandas as pd
from bs4 import BeautifulSoup
import requests
import os
import json
import requests
import copy
import tenacity
import xml.etree.ElementTree as ET

from logging import getLogger
logger = getLogger(__name__)


PMID_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term="
SUMMARY_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id="
COVERTER_BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids="
PMC_BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi?verb=GetRecord&identifier=oai:pubmedcentral.nih.gov:{pmcid}&metadataPrefix=oai_dc"
PUBMED_EFETCH_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id="

DEFAULT_MAX_PAGE_SIZE = 100
BATCH_REQUEST_SIZE = 400


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
    

def get_response_with_retry(query, max_retries=5):
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util import Retry
    
    # Define the retry strategy
    retry_strategy = Retry(
        total=max_retries,  # Maximum number of retries
        status_forcelist=[429, 500, 502, 503, 504],  # HTTP status codes to retry on
    )
    # Create an HTTP adapter with the retry strategy and mount it to session
    adapter = HTTPAdapter(max_retries=retry_strategy)
    
    # Create a new session object
    session = requests.Session()
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    # Make a request using the session object
    response = session.get(query)
    return response
    

def pmid2papers(pmid_list: list[str], api_key: str = None):
    if len(pmid_list) == 0:
        return None, [], 0
    papers = _retrieve_abstract_from_efetch(pmid_list, api_key)
    return papers, "", len(pmid_list)

def _parse_xml_recursively(element):
    child_dict = {}
    if element.text and element.text.strip():
        child_dict['text'] = element.text.strip()

    for child in element:
        if child.tag not in child_dict:
            child_dict[child.tag] = []
        child_dict[child.tag].append(_parse_xml_recursively(child))

    # Simplify structure when there's only one child or text
    for key in child_dict:
        if len(child_dict[key]) == 1:
            child_dict[key] = child_dict[key][0]
        elif not child_dict[key]:
            del child_dict[key]

    return child_dict


def _parse_article_xml_to_dict(article):
    results = {}
    dict_obj  = _parse_xml_recursively(article)

    # get article information
    article = dict_obj.get("MedlineCitation", {}).get("Article", {})

    # get the fields correspondingly
    results['PMID'] = dict_obj.get('MedlineCitation', {}).get('PMID', {}).get('text', '')

    # get the journal title
    journal = article.get('Journal', {}).get('Title', {}).get('text', '')
    results["Journal"] = journal

    # get pub date
    date = article.get('Journal', {}).get('JournalIssue', {})
    publication_year = date.get('PubDate', {}).get('Year', {}).get('text', '')
    publication_month = date.get('PubDate', {}).get('Month', {}).get('text', '')
    publication_day = date.get('PubDate', {}).get('Day', {}).get('text', '')
    results['Year'] = publication_year
    results['Month'] = publication_month
    results['Day'] = publication_day

    # get the title
    article_title = article.get('ArticleTitle', {}).get('text', '')
    results['Title'] = article_title

    # publication type
    publication_type = article.get('PublicationTypeList', {}).get('PublicationType', [])
    if len(publication_type) > 0:
        pubtype_list = []
        if isinstance(publication_type, dict):
            publication_type = [publication_type]
        for pt in publication_type:
            if isinstance(pt, dict):
                pubtype_list.append(pt.get('text', ''))
            else:
                pubtype_list.append(pt)
        publication_type = ", ".join(pubtype_list)
    else:
        publication_type = ""
    results['Publication Type'] = publication_type

    # authors
    author_names = article.get('AuthorList', {}).get('Author', [])
    authors = []
    if len(author_names) > 0:
        if isinstance(author_names, dict):
            author_names = [author_names]
        for author in author_names:
            last_name = author.get('LastName', {}).get('text', '')
            first_name = author.get('ForeName', {}).get('text', '')
            authors.append(f"{first_name} {last_name}")
        authors = ", ".join(authors)
    else:
        authors = ""
    results['Authors'] = authors

    # get the abstract
    abstracts = article.get('Abstract', {}).get('AbstractText', [])
    abstract_texts = []
    if len(abstracts) > 0:
        if isinstance(abstracts, dict):
            abstracts = [abstracts]
        for abstract in abstracts:
            if isinstance(abstract, dict):
                abstract_text = abstract.get('text', "")
            else:
                abstract_text = abstract
            abstract_texts.append(abstract_text)
        abstract_texts = "\n".join(abstract_texts)
    else:
        abstract_texts = ""
    results['Abstract'] = abstract_texts
    return results

def _parse_book_xml_to_dict(book):
    results = {}
    dict_obj  = _parse_xml_recursively(book)
    book = dict_obj.get("BookDocument")

    # get book information
    pmid = book.get("PMID", {}).get("text", "")
    results['PMID'] = pmid

    # get the book title
    book_title = book.get("Book", {}).get("BookTitle", {}).get("text", "")
    results['Title'] = book_title

    # pub date
    date = book.get("Book", {}).get('PubDate', {})
    publication_year = date.get('Year', {}).get('text', '')
    publication_month = date.get('Month', {}).get('text', '')
    publication_day = date.get('Day', {}).get('text', '')
    results['Year'] = publication_year
    results['Month'] = publication_month
    results['Day'] = publication_day

    # authors
    author_names = book.get('AuthorList', {}).get('Author', [])
    authors = []
    if len(author_names) > 0:
        if isinstance(author_names, dict):
            author_names = [author_names]
        for author in author_names:
            last_name = author.get('LastName', {}).get('text', '')
            first_name = author.get('ForeName', {}).get('text', '')
            authors.append(f"{first_name} {last_name}")
        authors = ", ".join(authors)
    else:
        authors = ""
    results['Authors'] = authors

    # get the abstract
    abstracts = book.get('Abstract', {}).get('AbstractText', [])
    abstract_texts = []
    if len(abstracts) > 0:
        if isinstance(abstracts, dict):
            abstracts = [abstracts]
        for abstract in abstracts:
            if isinstance(abstract, dict):
                abstract_text = abstract.get('text', "")
            else:
                abstract_text = abstract
            abstract_texts.append(abstract_text)
        abstract_texts = "\n".join(abstract_texts)
    else:
        abstract_texts = ""

    # get pub type
    publication_type = book.get('PublicationType', {}).get('text', '')
    results['Publication Type'] = publication_type
    return results

def _retrieve_abstract_from_efetch(pmids, api_key):
    """Retrieve the abstract from the efetch API."""
    all_abstracts = []
    for i in range(0, len(pmids), BATCH_REQUEST_SIZE):
        pmid_subset = pmids[i:i+BATCH_REQUEST_SIZE]
        pmid_str = ','.join(pmid_subset)
        query = PUBMED_EFETCH_BASE_URL + pmid_str + "&retmode=xml" + "&api_key=" + api_key
        logger.info(f"Abstract Query: {query}")
        response = get_response_with_retry(query)
        if response.status_code != 200:
            continue
        else:
            response = response.text
            tree = ET.fromstring(response)
            articles = tree.findall(".//PubmedArticle")
            for article in articles:
                try:
                    article_dict = _parse_article_xml_to_dict(article)
                    all_abstracts.append(article_dict)
                except:
                    continue

            # for books
            books = tree.findall(".//PubmedBookArticle")
            if len(books) > 0:
                for book in books:
                    try:
                        book_dict = _parse_book_xml_to_dict(book)
                        all_abstracts.append(book_dict)
                    except:
                        pass
    
    output_abstracts = pd.DataFrame.from_records(all_abstracts)
    return output_abstracts

class PubmedAPIWrapper:
    """A wrapper class for the pubmed API.
    """
    def __init__(self, retry=1):
        self.retry = retry        

    def __call__(self, inputs, exist_pmid=[], api_key=None, tool_name="trialmind", email="trialmind@gmail.com"):
        return self._run(inputs, exist_pmid, api_key, tool_name, email)

    def build_search_query_and_get_pmid(self, inputs, api_key):
        query = self._build_query(inputs, api_key)
        # get the response
        err_msg = ""
        for i in range(self.retry):
            try:
                response = self._get_response(query)
                if response.status_code == 200:
                    break
                else:
                    logger.error(f"Error: {response.text}\nRetry {i+1} times")
                    err_msg = response.text
            except:
                err_msg = traceback.format_exc()
                logger.error(err_msg)
                break

        if err_msg != "":
            return [], query, 0
    
        if response.status_code != 200:
            logger.error(f"Error: {response.text}\nRetry {i+1} times")
            err_msg = response.text

        try:
            # parse the response to a list of pmid and pmc id
            pmid_list, total_count = self._parse_response(response.text)
            # join the exist pmid list
            pmid_list = list(set(pmid_list))
            logger.info(f"Retrieved {len(pmid_list)} PMIDs")
        except:
            err_msg = traceback.format_exc()
            pmid_list = []
            logger.error(err_msg)

        return pmid_list, query, total_count

    def _run(self, inputs, exist_pmid, api_key, tool_name, email):
        # parse the inputs
        # send out the request
        # Start new query to get all pmids
        search_query = ""
        if len(exist_pmid) > 0:
            exist_pmid = [str(each_id) for each_id in exist_pmid]
            pmid_list = list(set(exist_pmid))
        else:
            # build search query based on user input
            pmid_list, search_query, total_count = self._build_search_query_and_get_pmid(inputs, api_key)

        # retrieve the content of the paper from the input pmid list
        papers, summary_query, total_count = self._retrieve_papers_from_pmid(pmid_list, api_key)

        if search_query == "":
            search_query = summary_query

        return papers, search_query, total_count

    def _retrieve_papers_from_pmid(self, pmid_list, api_key):
        if len(pmid_list) == 0:
            return None, [], 0
        return pmid2papers(pmid_list, api_key)
  
    def _build_search_query_and_get_pmid(self, inputs, api_key):
        query = self._build_query(inputs, api_key)
        err_msg = ""
        response = get_response_with_retry(query)
    
        if response.status_code != 200:
            err_msg = response.text
            return [], query, 0

        try:
            # parse the response to a list of pmid and pmc id
            pmid_list, total_count = self._parse_response(response.text)
            # join the exist pmid list
            pmid_list = list(set(pmid_list))
            logger.info(f"Retrieved {len(pmid_list)} PMIDs")
        except:
            total_count = 0
            err_msg = traceback.format_exc()
            pmid_list = []
            logger.error(err_msg)
        return pmid_list, query, total_count
        
    def _build_query(self, inputs, api_key):
        """Parse the inputs and convert them to the query parameters."""
        input_dict = copy.deepcopy(inputs)
        query_parts = []
        
        # Handle page size
        page_size = input_dict.get('page_size', DEFAULT_MAX_PAGE_SIZE)

        logger.info(f"Input Dict: {input_dict}")
        # Handle journal names
        if input_dict.get('journal', []) and len(input_dict['journal']) > 0:
            journal = '[journal]+OR+'.join(list(set(input_dict['journal'])))
            query_parts.append(f"{journal}")
            query_parts.append('[journal]+AND+')
        
        # Handle authors
        if input_dict.get('author', []) and len(input_dict['author']) > 0:
            authors = '[author]+OR+'.join(list(set(input_dict['author'])))
            query_parts.append(f"{authors}")
            query_parts.append('[author]+AND+')
            
        # Handle publisher
        if input_dict.get('publisher', []) and len(input_dict['publisher']) > 0:
            publisher = '[publisher]+OR+'.join(list(set(input_dict['publisher'])))
            query_parts.append(f"{publisher}")
            query_parts.append('[publisher]+AND+')
        
        if 'keywords' in input_dict:
            kw_map = input_dict['keyword_map']
            key_query = []
            for k in kw_map:
                cur_query = '('
                cur_query += '+OR+'.join(kw_map[k])
                cur_query += ')'
                key_query.append(cur_query)
            oper = input_dict['keywords']['OPERATOR']
            if oper == 'OR':
                key_query = '+OR+'.join(key_query)
            else:
                key_query = '+AND+'.join(key_query)
            query_parts.append(f"{key_query}")
            
        # Handle mindate
        if input_dict.get('min_date', '') and len(input_dict['min_date']) > 0:
            query_parts.append(f"&mindate={input_dict['min_date']}")
            
        # Handle maxdate
        if input_dict.get('max_date', '') and len(input_dict['max_date']) > 0:
            query_parts.append(f"&maxdate={input_dict['max_date']}")
            
        # Handle reldate
        if input_dict.get('reldate', ''):
            query_parts.append(f"&reldate={input_dict['reldate']}")
            
        # Handle sort order
        if input_dict.get('sort', '') and len(input_dict['sort']) > 0:
            query_parts.append(f"&sort={input_dict['sort']}")
            
        # Handle retmax
        query_parts.append(f"&retmax={page_size}&retmode=json")
        if api_key is not None:
            query_parts.append(f"&api_key={api_key}")
        logger.info(f"Query parts: {query_parts}")
        query= PMID_BASE_URL + ''.join(query_parts)
        return query
    
    def _parse_response(self, response):
        """Parse the response from the API call."""
        response_dict = json.loads(response)
        pmid_list = response_dict['esearchresult']['idlist']
        total_count = response_dict['esearchresult']['count']
        return pmid_list, total_count

    @tenacity.retry(wait=tenacity.wait_fixed(2), stop=tenacity.stop_after_attempt(3))
    def _get_response(self, query):
        # get the response
        response = requests.get(query)
        return response

def pmid2biocxml(pmid):
    base_url = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/{pmid}/unicode"
    if not isinstance(pmid, list): pmid = [pmid]
    res = []
    for pmid_ in pmid:
        request_url = base_url.format(pmid=pmid_)
        response = requests.get(request_url)
        res.append(response.text)
    return res

def parse_bioc_xml(path):
    """
    Parse BioC XML text to a list of dictionary of each passage
    and its metadata

    Parameters
    ----------
    path: str
        Path to the BioC formatted XML file.
        Or the input xml text.

    Return
    ------
    dict_bioc: list
        A list contains all dictionary of passage with its metadata.
        Metadata includes 'pmid', 'pmc', 'section' name of an article, and section 'text'
    """
    if os.path.exists(path):
        bioc_text = open(path, "r").read()
    else:
        bioc_text = path
    soup = BeautifulSoup(bioc_text, features="xml")
    passages = soup.find_all("passage")
    passage_dic = list()
    ref_dic = list()
    table_dic = list()
    fig_dic = list()
    author_contribution = list()
    comp_int = list()
    supplementary_material = list()

    for passage in passages:
        infons = passage.find_all("infon")
        section = [info.text for info in infons if info.get("key") == "section_type"]
        if len(section) == 0:
            section = ""
        else:
            section = section[0]

        pmid = [info.text for info in infons if info.get("key") == "article-id_pmid"]
        if len(pmid) == 0:
            pmid = ""
        else:
            pmid = pmid[0]

        pmcid = [info.text for info in infons if info.get("key") == "article-id_pmc"]
        if len(pmcid) == 0:
            pmcid = ""
        else:
            pmcid = pmcid[0]


        if section == "REF":
            texts = passage.find_all("text")
            texts = ". ".join([t.text for t in texts])
            ref_dic.append(
                {
                    "pmid": pmid,
                    "pmc": pmcid,
                    "section": section,
                    "content": texts,
                }
            )

        elif section == "TABLE":
            tab_ele_type = passage.find("infon", {"key": "type"})
            if tab_ele_type is not None: tab_ele_type = tab_ele_type.text
            tab_id = passage.find("infon", {"key": "id"})
            if tab_id is not None: tab_id = tab_id.text
            texts = passage.find_all("text")
            texts = ". ".join([t.text for t in texts])
            table_dic.append(
                {
                    "pmid": pmid,
                    "pmc": pmcid,
                    "section": section,
                    "tab_id": tab_id,
                    "tab_ele_type": tab_ele_type,
                    "content": texts,
                }
            )

        elif section == "FIG":
            fig_id = passage.find("infon", {"key": "id"})
            if fig_id is not None: fig_id = fig_id.text
            fig_caption = passage.find("infon", {"key": "caption"})
            if fig_caption is not None: fig_caption = fig_caption.text
            texts = passage.find_all("text")
            texts = ". ".join([t.text for t in texts])
            fig_dic.append(
                {
                    "pmid": pmid,
                    "pmc": pmcid,
                    "section": section,
                    "fig_id": fig_id,
                    "fig_caption": fig_caption,
                    "content": texts,
                }
            )

        elif section == "AUTH_CONT":
            texts = passage.find_all("text")
            texts = ". ".join([t.text for t in texts])
            author_contribution.append(
                {
                    "pmid": pmid,
                    "pmc": pmcid,
                    "section": section,
                    "content": texts,
                }
            )

        elif section == "COMP_INT":
            texts = passage.find_all("text")
            texts = ". ".join([t.text for t in texts])
            comp_int.append(
                {
                    "pmid": pmid,
                    "pmc": pmcid,
                    "section": section,
                    "content": texts,
                }
            )

        elif section == "SUPPL":
            texts = passage.find_all("text")
            texts = ". ".join([t.text for t in texts])
            supplementary_material.append(
                {
                    "pmid": pmid,
                    "pmc": pmcid,
                    "section": section,
                    "content": texts,
                }
            )

        else:
            texts = passage.find_all("text")
            texts = ". ".join([t.text for t in texts])
            passage_dic.append(
                {
                    "pmid": pmid,
                    "pmc": pmcid,
                    "section": section,
                    "content": texts,
                }
            )

    return {
        "passage": passage_dic,
        "ref": ref_dic,
        "table": table_dic,
        "figure": fig_dic,
        "author_contribution": author_contribution,
        "competing_interest": comp_int,
        "supplementary_material": supplementary_material,
    }


