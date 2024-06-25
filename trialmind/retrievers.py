import asyncio
import time
import logging
logger = logging.getLogger(__name__)

def _async_execute(async_function, **kwargs):
    from concurrent.futures import ThreadPoolExecutor
    try:
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(1) as executor:
            results = executor.submit(lambda: asyncio.run(async_function(**kwargs)))
            results = results.result()
    except RuntimeError:
        results = async_function(**kwargs)
        results = asyncio.run(results)
    return results

async def async_fetch_relevant_documents(retriever, query):
    return retriever.get_relevant_documents(query=query)

async def async_process_queries(queries, retriever):
    tasks = []
    for q in queries:
        task = asyncio.create_task(async_fetch_relevant_documents(retriever, q))
        tasks.append(task)
    results = await asyncio.gather(*tasks)
    return [doc for sublist in results for doc in sublist]

def semantic_filtering_fn(splited_docs, queries, semantic_filtering_top_k):
    """Args:
    splited_docs: list of strings, each string is a snippet of the document
    queries: list of strings, each string is a query
    semantic_filtering_top_k: int, number of top k documents to return
    """
    from langchain_community.retrievers import BM25Retriever
    from langchain.docstore.document import Document
    if isinstance(queries, str):
        queries = [queries]
    # build the indexed once, and search by filtering the input ids
    st = time.time()
    doc_blocks = []
    for i, splited in enumerate(splited_docs):
        doc_blocks_ = Document(page_content=splited, metadata={"index": i})
        doc_blocks.append(doc_blocks_)
    
    # build the vectorstore and retrieve
    retriever = BM25Retriever.from_documents(doc_blocks, k=semantic_filtering_top_k)
    selected_list = _async_execute(async_function=async_process_queries, queries=queries, retriever=retriever)
    logger.info(f"Time to build the vectorstore and retrieve: {time.time()-st}")
    return selected_list

def split_text_into_chunks(text, chunk_size=1000, chunk_overlap=20):
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    if isinstance(text, list): # already been split
        blocks = text
    else:
        splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
        )
        blocks = splitter.create_documents([text])
        blocks = [t.page_content for t in blocks]
    return blocks

def combine_blocks_text(blocks, format="xml"):
    from langchain.docstore.document import Document
    # combine the blocks
    new_blocks = []
    for i, block in enumerate(blocks):
        if isinstance(block, Document):
            block = block.page_content
        new_blocks.append(block)
    new_blocks = list(set(new_blocks))
    if format == "xml":
        new_block_strs = [f"<source id=\"{i}\"><content>{block}</content></source>" for i,block in enumerate(new_blocks)]
    else:
        new_block_strs = [f"[[citation:{i}]] {block}" for i,block in enumerate(new_blocks)]
    combined = '\n\n'.join(new_block_strs)
    return combined, new_blocks