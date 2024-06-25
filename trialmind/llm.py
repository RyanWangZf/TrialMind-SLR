from typing import Union, Literal
from langchain_core.utils.function_calling import convert_to_openai_function

from .llm_utils.openai import call_openai
from .llm_utils.openai_async import batch_call_openai
from .llm_utils.openai_async import batch_function_call_openai

def call_llm(
    prompt_template,
    inputs,
    llm="openai-gpt-4o",
    temperature=0.0,
    streaming=False,
    stop_words=[],
):
    """Call Chat LLM models, with text inputs and text outputs.

        Args:
            prompt_template (str or BasePromptTemplate): The prompt template to be fed with user's request.
                e.g., "What is the difference between {item1} and {item2}".
            inputs (dict): The inputs to be fed to the prompt template. Should match the placeholders
                in the prompt template, e.g., {"item1": "apple", "item2": "orange"}.
            llm: (str): The name of the LLM model to be used. 
                Support: "gpt-35", "gpt-4", "sonnet", "hiku", "claude", and "titan"
            temperature (float): The temperature for the LLM model.
                The higher the temperature, the more creative the text.
                The lower the temperature, the more predictable the text.
                The default value is 0.0.
            streaming (bool): Whether to use streaming mode.
                The default value is False.
            stop_words (list[str]): The stop words to be used in the LLM model.
                The default value is an empty list.

        Returns:
            str: The response from the LLM model.
    """
    messages = _batch_inputs_to_messages(prompt_template, [inputs])[0]
    response = call_openai(
        llm=llm,
        messages=messages,
        temperature=temperature,
        stop=stop_words,
        stream=streaming
    )
    return _wrap_response_openai(response)


def batch_call_llm(
    prompt_template,
    batch_inputs,
    llm: Union[str, Literal[
        "openai-gpt-35",
        "openai-gpt-4",
        "openai-gpt-4o",
    ]],
    temperature=0.0,
    batch_size=None,
    ):
    """Call Chat LLM models on a batch of inputs in parallel, with text inputs and text outputs.

    Args:
        prompt_template (str): The prompt template to be fed with user's request.
            e.g., "What is the difference between {item1} and {item2}".
        batch_inputs (List[dict]): A batch of inputs to be fed to the prompt template. Should match the placeholders
            in the prompt template, e.g., {"item1": "apple", "item2": "orange"}.
        output_parser (langchain_core.output_parsers, optional): The output parser to parse the output from the LLM model.
            The default value is `langchain_core.output_parsers.StrOutputParser()`.
        llm: (str): The name of the LLM model to be used. 
        temperature (float): The temperature for the LLM model.
            The higher the temperature, the more creative the text.
            The lower the temperature, the more predictable the text.
            The default value is 0.0.
        batch_size (int): The batch size for the batch call. Define
            the number of inputs to be processed in parallel.
            The default value is None, will proceed with all inputs in one batch.

    Returns:
        str: The response from the LLM model.
    """
    batch_messages = _batch_inputs_to_messages(prompt_template=prompt_template, batch_inputs=batch_inputs)
    if batch_size is not None:
        results = []
        for i in range(0, len(batch_messages), batch_size):
            batch_results = batch_call_openai(batch_messages[i:i+batch_size], llm=llm, temperature=temperature)
            results.extend(batch_results)
    else:
        results = batch_call_openai(batch_messages, llm=llm, temperature=temperature)
    return results


def batch_function_call_llm(
    prompt_template,
    batch_inputs,
    schema,
    llm: Union[str, Literal[
        "openai-gpt-35",
        "openai-gpt-4",
        "openai-gpt-4o",
    ]],
    temperature=0.0,
    batch_size=None,
):
    """
    Call LLM models with function call with a batch of inputs, so it outputs
        the structured data instead of text, strictly following
        the schema.

        Args:
            prompt_template (str or PromptTemplateBase): The prompt template to be fed with user's request.
            batch_inputs (list[dict]): The list of inputs to be fed to the prompt template.
            schema (pydantic.v1.BaseModel): The schema of the output data specified in Pydantic.
                Refer to "trialmind/TrialSearch/schema.ClinicalTrialQuery" for an example.
            llm: (str): The name of the LLM model to be used. 
                Currently, only "gpt-4" and "gpt-35" support `function call`.
            temperature (float): The temperature for the LLM model.
                The higher the temperature, the more creative the text.
                The lower the temperature, the more predictable the text.
                The default value is 0.0.
            batch_size (int): The batch size for the batch call. Define
                the number of inputs to be processed in parallel.
                The default value is None, will proceed with all inputs in one batch.

        Returns:
            dict: The structured data output from the LLM model.
    """
    schema_desc = convert_to_openai_function(schema)
    tools = [
        {
            "type": "function",
            "function": schema_desc,
        }
    ]
    batch_messages = _batch_inputs_to_messages(prompt_template=prompt_template, batch_inputs=batch_inputs)
    if batch_size is not None:
        results = []
        for i in range(0, len(batch_messages), batch_size):
            batch_results = batch_function_call_openai(batch_messages[i:i+batch_size], llm=llm, tools=tools, temperature=temperature)
            results.extend(batch_results)
    else:
        results = batch_function_call_openai(batch_messages, llm=llm, tools=tools, temperature=temperature)
    return results


def _batch_inputs_to_messages(prompt_template, batch_inputs):
    # build messages for the openai
    batch_messages = []
    for i, batch_input in enumerate(batch_inputs):
        prompt_content = prompt_template.format(**batch_input)
        messages = [
            {
                "role": "user",
                "content": prompt_content
            }
        ]
        batch_messages.append(messages)
    return batch_messages

def _wrap_response_openai(response):
    return response.choices[0].message.content