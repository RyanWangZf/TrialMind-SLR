import json
import re
import tempfile
import os
import io
from typing import List, Dict, Union, Optional

import pandas as pd

from .llm import (
    call_llm, 
    batch_call_llm,
    batch_function_call_llm
)
from .retrievers import (
    split_text_into_chunks,
    combine_blocks_text,
    semantic_filtering_fn
)
from .prompts.search_query import (
    PRIMARY_TERM_EXTRACTION, 
    SEARCH_TERM_EXTRACTION
)
from .prompts.extraction import (
    STUDY_RESULTS_FORMATTING,
    RESULT_TABLE_EXTRACTION,
    STUDY_FIELDS_EXTRACTION,
    STUDY_RESULTS_STANDARDIZATION,
    RESULT_TABLE_TEMPLATE,
    )
from .prompts.screening import LITERATURE_SCREENING_FC
from .prompts.screening_criteria import SCREENING_CRITERIA_GENERATION
from .pubmed import ReqPubmedFull, ReqPubmedID


from logging import getLogger
logger = getLogger(__name__)

def extract_json(input_text):
    # Pattern to match content between ```json and ```
    json_pattern = r"```json\n([\s\S]*?)\n```"
    match = re.search(json_pattern, input_text)

    if match:
        # Extract JSON content between ```json and ```
        return match.group(1)
    else:
        # Pattern to match content between {{ and }}
        curly_pattern = r"\{\{([\s\S]*?)\}\}"
        match = re.search(curly_pattern, input_text)
        if match:
            output = match.group(1)
            return output
        else:
            # Attempt to parse the entire input as JSON
            try:
                json.loads(input_text)
                # If no exception is raised, the entire input is valid JSON
                return input_text
            except json.JSONDecodeError:
                # Input is not valid JSON
                return None


def parse_json_outputs(outputs: List[str]) -> List[Dict]:
    parsed_outputs = []
    for output in outputs:
        output = extract_json(output)
        try:
            output = json.loads(output)
        except:
            output = {}
        parsed_outputs.append(output)
    return parsed_outputs


class SearchQueryGeneration:
    """
    Input the user's input research question, generate the search query for the searching clinical studies.

    Args:
        population (str): The population of the research question.
        intervention (str): The intervention of the research question.
        comparator (str): The comparator of the research question.
        outcome (str): The outcome of the research question.
        llm (str): The language model to use for the search query generation. Default is "gpt-4".
    """
    def __init__(self):
        pass

    def run(self,
            population: str,
            intervention: str,
            comparator: str,
            outcome: str,
            llm: str="gpt-4"
        ):
        # get initial term 
        terms = self._run_init_term_generation(population, intervention, comparator, outcome, llm=llm)
        terms = 'AND'.join([f'({k})' for k in terms])
        logger.info(f"Generate initial search terms: {terms}")

        # find reference pubmed papers
        pmids = self._run_pubmed_id_search(terms)
        logger.info(f"Fetch initial reference pubmed paper ids {pmids}")
        pubmed_reference_text = self._run_pubmed_full_search(pmids)

        # generate the final search query
        outputs = self._run_final_search_query_generation(population, intervention, comparator, outcome, pubmed_reference_text, llm=llm)

        return {
            "conditions": outputs["conditions"],
            "treatments": outputs["treatments"],
            "outcomes": outputs["outcomes"]
        }

    def _run_init_term_generation(self, population, intervention, comparator, outcome, llm):
        outputs = call_llm(PRIMARY_TERM_EXTRACTION, {"P": population, "I": intervention, "C": comparator, "O": outcome}, llm=llm)
        # remove the prefix "```json\n" and suffix "\n```"
        # using regex
        outputs = parse_json_outputs([outputs])[0]
        return outputs["terms"]
    
    def _run_pubmed_id_search(self, terms):
        req = ReqPubmedID()
        pmids = req.run(term=terms, retmax=7)
        return pmids
    
    def _run_pubmed_full_search(self, pmids):
        req = ReqPubmedFull()
        fetched_pubmed_data = req.run(pmids)
        pubmed_reference_text = '\n'.join(f"{idx+1}. {d['title']}\nAbstract: {d['abstract']}" 
                                          for idx, d in enumerate(fetched_pubmed_data))
        return pubmed_reference_text
    
    def _run_final_search_query_generation(self, population, intervention, comparator, outcome, pubmed_reference_text, llm):
        outputs = call_llm(SEARCH_TERM_EXTRACTION, {"P": population, "I": intervention, "C": comparator, "O": outcome, "pubmed_reference_text": pubmed_reference_text}, llm=llm)
        logger.info(f"Final search query: {outputs}")

        outputs = parse_json_outputs([outputs])[0]

        # get the terms
        core_conditions = outputs.get("step 2", {}).get("CORE_CONDITIONS", [])
        core_treatments = outputs.get("step 2", {}).get("CORE_TREATMENTS", [])
        core_outcomes = outputs.get("step 2", {}).get("CORE_OUTCOMES", [])

        expand_conditions = outputs.get("step 3", {}).get("EXPAND_CONDITIONS", [])
        expand_treatments = outputs.get("step 3", {}).get("EXPAND_TREATMENTS", [])
        expand_outcomes = outputs.get("step 3", {}).get("EXPAND_OUTCOMES", [])

        conditions = list(set(core_conditions + expand_conditions))
        treatments = list(set(core_treatments + expand_treatments))
        outcomes = list(set(core_outcomes + expand_outcomes))

        return {
            "conditions": conditions,
            "treatments": treatments,
            "outcomes": outcomes
        }


class ScreeningCriteriaGeneration:
    """
    Input the user's input research question, generate the screening criteria for the screening clinical studies.

    Args:
        population (str): The population of the research question.
        intervention (str): The intervention of the research question.
        comparator (str): The comparator of the research question.
        outcome (str): The outcome of the research question.
        num_title_criteria (int): The number of title criteria to generate. Default is 3.
        num_abstract_criteria (int): The number of abstract criteria to generate. Default is 3.
        llm (str): The language model to use for the screening criteria generation. Default is "gpt-4".
    """
    def __init__(self):
        pass

    def run(
        self,
        population: str,
        intervention: str,
        comparator: str,
        outcome: str,
        num_title_criteria: int=3,
        num_abstract_criteria: int=3,
        llm: str="gpt-4"
        ):
        outputs = call_llm(
            SCREENING_CRITERIA_GENERATION, 
            {"P": population, 
             "I": intervention, 
             "C": comparator, 
             "O": outcome, 
             "num_title_criteria": num_title_criteria, 
             "num_abstract_criteria": num_abstract_criteria
            }, 
            llm=llm
            )
        
        if outputs is not None:
            outputs = parse_json_outputs([outputs])[0]

        title_criteria = outputs.get("TITLE_CRITERIA", [])
        content_criteria = outputs.get("CONTENT_CRITERIA", [])
        eligibility_analysis = outputs.get("ELIGIBILITY_ANALYSIS", [])

        return {
            "title_criteria": title_criteria,
            "content_criteria": content_criteria,
            "eligibility_analysis": eligibility_analysis
        }


class StudyCharacteristicsExtraction:
    """
    Extract the structured data from a clinical study, based on user's request if provided.

    Args:
        papers (list[str or list[str]]): A list of clinical study papers' raw content in text or in a list of string.
            If the input is a list of string, each string is a text block from the paper.
            If the input is a single string, the API will try to cut the text into blocks,
            which is for generating the citations from the paper.
        fields (List[str]): The fields to extract from the clinical study papers. 
           Each element is natural language description of which information this field is about.
           It is suggested to be in the format of "[Field Name], [Data Type], [Description]".
        llm (str): The language model to use for the extraction. Default is "gpt-4".
        batch_size (int): The batch size for the batch call. Default is 5.
            Too large batch size may cause the request failed.
        semantic_filtering (bool): Whether to use semantic ranking to only keep the most relevant blocks
            so to reduce the number of blocks to be processed. Default is False.
        semantic_filtering_top_k (int): The top k blocks to keep after the semantic filtering. Default is 20.
    """
    DEFAULT_FIELDS = [
        "Study Name, string, the study's alias, usually be in the format of FirstAuthorYear",
        "Study Type, string, if the study is randomized controlled trial, observational study, or others",
        "Study Year, date, the study's year",
        "Location: which countries the study was conducted in",
        "Phase, string: in which phase this clinical trial is in, e.g., phase 1, phase 2, phase 3, or phase 4",
        "Conditions, list of string, the conditions or diseases the study is investigating",
        "Treatments, list of string, the primary treatment or intervention used in the study",
        "Comparison, list of string, the comparison treatment or intervention used in the study",
        "Num Patients, int, how many participants are in the study",
        "Mean Age, continuous, the average age of the participants",
        "Age Range, string, the age range of the participants",
        ]
    def __init__(self):
        pass

    def run(self,
        papers: list[Union[str,list[str]]],
        fields: list[str]=[],
        llm: str="gpt-4",
        batch_size: int = None,
        semantic_filtering: bool = False,
        semantic_filtering_top_k: int = 20,
        ):
        # get the fields
        fields = fields if len(fields) > 0 else self.DEFAULT_FIELDS
        fields_info = '\n'.join([f"<field id={idx+1}>\"{field}\"</field>" for idx, field in enumerate(fields)])

        # build batch inputs
        batch_inputs = []
        splited_docs = []
        for i, paper in enumerate(papers):
            splited = split_text_into_chunks(paper)
            splited_docs.append(splited)

        if semantic_filtering:
            new_splited_docs = []
            for splited_doc in splited_docs:
                splited_doc = semantic_filtering_fn(splited_doc, fields, semantic_filtering_top_k)
                new_splited_docs.append(splited_doc)
            splited_docs = new_splited_docs
            
        unique_splited_docs = []
        for i, splited in enumerate(splited_docs):
            combined, splited = combine_blocks_text(splited)
            unique_splited_docs.append(splited)
            batch_inputs.append({
                "paper_content": combined,
                "fields": fields_info
            })
        
        # call llm
        outputs = batch_call_llm(STUDY_FIELDS_EXTRACTION, batch_inputs, llm=llm, batch_size=batch_size)
        parsed_outputs = parse_json_outputs(outputs)

        # attach the cited blocks to the outputs
        cited_parsed_outputs = []
        for i, output in enumerate(parsed_outputs):
            blocks = unique_splited_docs[i]
            new_output = []
            for field_output in output:
                src_ids = field_output.get("source_id", [])
                cited = []
                for src_id in src_ids:
                    cited.append(blocks[src_id])
                field_output["cited_blocks"] = cited
                new_output.append(field_output)
            cited_parsed_outputs.append(new_output)
        return cited_parsed_outputs
    
class LiteratureScreening:
    """Pass the papers through the screening criteria to determine if they are relevant to the research question.
    The input contains a list of criteria for screening the papers, and the papers to be screened.

    Args:
        papers: A list of clinical study papers' raw content in text, to be screened.
        criteria: A list of screening criteria for the papers.
        llm: The language model to use for the screening. Default is "gpt-4".
    """
    def __init__(self):
        pass

    def run(self,
        population: str,
        intervention: str,
        comparator: str,
        outcome: str,
        papers: list[str],
        criteria: list[str],
        llm: str="gpt-4",
        batch_size: int = None,
        ):

        # build the criteria text with index
        criteria_text = [f"{idx+1}. {c}" for idx, c in enumerate(criteria)]
        n_criteria = len(criteria_text)

        # build batch inputs
        batch_inputs = []
        for paper in papers:
            batch_inputs.append({
                "P": population,
                "I": intervention,
                "C": comparator,
                "O": outcome,
                "paper_content": paper,
                "criteria_text": criteria_text,
                "num_criteria": n_criteria
            })

        # call llm
        from langchain.pydantic_v1 import BaseModel, validator, Field, conlist
        from typing import Dict, Literal
        class PaperEvaluation(BaseModel):
            evaluations: conlist(Literal['YES', 'NO', 'UNCERTAIN'], min_items=n_criteria, max_items=n_criteria) = Field(description=f"Evaluations for {n_criteria} criteria, must be of length {n_criteria}")
        outputs = batch_function_call_llm(LITERATURE_SCREENING_FC, batch_inputs, PaperEvaluation, llm=llm, batch_size=batch_size)

        # try to fix the predictions if not met the output format
        parsed_outputs = self._check_outputs(outputs, n_criteria)
        return parsed_outputs
    
    def _check_outputs(self, outputs, n_criteria):
        # check if the outputs are in the correct format
        parsed_outputs = []
        for output in outputs:
            try:
                evaluations = output.get("evaluations", [])
                if len(evaluations) != n_criteria:
                    evaluations = ["UNCERTAIN"] * n_criteria
                else:
                    evaluations = [e.upper() for e in evaluations]
                    evaluations = [e if e in ["YES", "NO", "UNCERTAIN"] else "UNCERTAIN" for e in evaluations]
            except:
                evaluations = ["UNCERTAIN"] * n_criteria
            parsed_outputs.append(evaluations)
        return parsed_outputs

class StudyResultExtraction:
    """Extract the target outcome measurement results from the given papers.
    
    Args:
        outcome: The target outcome measurement.
        papers: A list of clinical study papers' raw content in text.
        llm: The language model to use for the extraction. Default is "gpt-4".
    """
    def __init__(self):
        pass

    def run(self,
        outcome: str,
        papers: list[str],
        cohort: str="all arms of the study",
        llm: str="gpt-4",
        batch_size: int = None,
        ):
        outputs = self._run_outcome_extraction(papers, outcome, cohort, llm, batch_size)
        return outputs

    def _run_outcome_extraction(self, papers, outcome, cohort, llm, batch_size):
        batch_inputs = []
        for paper in papers:
            batch_inputs.append({
                "paper_content": paper,
                "target_outcome": outcome,
                "cohort": cohort,
            })
        outputs = batch_call_llm(RESULT_TABLE_EXTRACTION, batch_inputs, llm=llm, batch_size=batch_size)

        # parse outputs
        outputs = parse_json_outputs(outputs)
        return outputs


class StudyResultStandardization:
    """Given the raw extracted results, standardize the extracted results into a structured format.

    Args:
        population: The population of the research question.
        intervention: The intervention of the research question.
        comparator: The comparator of the research question.
        outcome: The target outcome measurement.
        data_type: The data type of the outcome measurement. It can be "binary", "continuous", "o-minus-e", or "generic".
        results: A list of extracted results from the papers.
        sandbox_id: The ID of the sandbox to connect to. If not found, this API will not be able to execute the code.
        llm: The language model to use for the standardization. Default is "gpt-4".
    """
    # step 1: detect the variables from the input
    # step 2: write the python code to create the target table
    # step 3: write some examples to help LLMs understand what to do here.
    def __init__(self):
        pass

    def run(self,
        population: str,
        intervention: str,
        comparator: str,
        outcome: str,
        data_type: str, # ["binary", "continuous", "o-minus-e", "generic"],
        results: list[str],
        sandbox_id: Optional[str]=None,
        llm: str="gpt-4"
        ):
        # connect to the E2B sandbox with the given sandbox id
        if sandbox_id is not None and len(sandbox_id) > 0:
            from trialmind.sandbox import E2BSandbox
            self.sandbox = E2BSandbox(sandbox_id=sandbox_id)
        else:
            logger.warning("No sandbox id is provided. The API will not be able to execute the code!")
            self.sandbox = None

        # get the initial table
        outputs = self._run_initial_table_extraction(population, intervention, comparator, outcome, results, llm=llm)

        # run the standard table extraction
        output_code = self._run_standard_table_extraction_code_gen(
            population, intervention, comparator, outcome, outputs, data_type, llm
        )

        # run the generated python code to get the standard table results
        output_data = {}
        if self.sandbox is not None:
            output_data = self._execute_code_to_get_standard_table(
                outputs, 
                output_code
                )

        # build the final outputs
        # each output has: result, code, data
        # could be all none, or partial none
        final_outputs = []
        for index, extracted_ in enumerate(outputs):
            code = output_code.get(index, None)
            data = output_data.get(index, None)
            final_outputs.append({
                "raw_data": extracted_,
                "code": code,
                "standardized_data": data
            })
        return final_outputs

    def _run_standard_table_extraction_code_gen(self,
        population: str,
        intervention: str,
        comparator: str,
        outcome: str,
        results: list[dict],
        data_type: str,
        llm: str="gpt-4"
        ):
        from trialmind.DataScienceFlow.utils import extract_code

        data_structure = RESULT_TABLE_TEMPLATE.get(data_type, None)
        if data_structure is None:
            raise ValueError(f"data_type {data_type} is not supported.")
        else:
            target_output = data_structure["table"]
            target_desc = data_structure["desc"]

        # build batch inputs
        batch_inputs = []
        batch_input_indices = []
        for i, result in enumerate(results):
            if result is not None:
                batch_input_indices.append(i)
                # formulate the result better
                result_txt = self._build_result_text(result)
                batch_inputs.append(
                {
                    "population": population,
                    "intervention": intervention,
                    "comparator": comparator,
                    "outcome": outcome,
                    "raw_data": result_txt,
                    "target_output": target_output,
                    "desc": target_desc
                }
        )
        if len(batch_inputs) > 0:
            outputs = batch_call_llm(STUDY_RESULTS_FORMATTING, batch_inputs, llm=llm)
            # parse the outputs to extract the python code
            output_codes = []
            for output_code in outputs:
                try:
                    output_code = extract_code(output_code)
                except:
                    output_code = output_code
                output_codes.append(output_code)
            
            return {i: o for i, o in zip(batch_input_indices, output_codes)}
        else:
            return {}
        
    def _run_initial_table_extraction(self,
        population: str,
        intervention: str,
        comparator: str,
        outcome: str,
        results: list[str],
        llm: str="gpt-4"
        ):
        batch_inputs = []
        for result in results:
            batch_inputs.append({
                "population": population,
                "intervention": intervention,
                "comparator": comparator,
                "outcome": outcome,
                "results": result
            })
        outputs = batch_call_llm(STUDY_RESULTS_STANDARDIZATION, batch_inputs, llm=llm)
        
        # parse outputs
        outputs = parse_json_outputs(outputs)
        return outputs
    
    def _build_result_text(self, result):
        try:
            values = []
            for r in result:
                values_ = []
                for k, v in r.items():
                    values_.append(v)
                values.append(values_)
            columns = list(result[0].keys())
            df = pd.DataFrame(values, columns=columns)
            result_text = df.to_markdown()
            return result_text
            
        except:
            # if failed, return the original result
            return result
        
    def _execute_code_to_get_standard_table(self,
        results,
        codes,
        ):
        def _upload_to_sandbox(df):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmpfile:
                df.to_csv(tmpfile.name, index=False)
                # upload the dataframe to the sandbox
                remote_path = self.sandbox.upload_file(tmpfile.name)
            os.remove(tmpfile.name)
            return remote_path
        
        # execute the code to get the standard table
        output_data = {}
        for index, result in enumerate(results):
            code = codes.get(index, {})
            output_filename = "result_table_{}.csv".format(index)
            save_output_code = f"df.to_csv('{output_filename}', index=False)"
            if code is None:
                continue
            
            # parse the result
            try:
                columns = list(result[0].keys())
                values = []
                for r in result: values.append(r.values())
                df = pd.DataFrame(values, columns=columns)
                filepath = _upload_to_sandbox(df)
                code = f"""import pandas as pd\ndf = pd.read_csv('{filepath}')\n{code}\n{save_output_code}"""
                stdout, stderr, artifacts = self.sandbox.run_python(code)

                # try to download the result from the artifacts
                for artifact in artifacts:
                    if artifact.file_name == output_filename:
                        # load the csv file from bytes content
                        csv_file_like_object = io.BytesIO(artifact.content)
                        data = pd.read_csv(csv_file_like_object)
                        output_data[index] = data.to_dict(orient='records')
                        break
                        
            except:
                continue
                
        # return the output data
        return output_data