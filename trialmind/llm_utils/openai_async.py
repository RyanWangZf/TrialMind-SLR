import pdb
import asyncio
from typing import List, Union
import httpx
from openai import AsyncOpenAI
from openai import AsyncAzureOpenAI
import tenacity
import json

OPENAI_MODEL_NAME_GPT4 = "gpt-4-turbo"  # new gpt-4-turbo
OPENAI_MODEL_NAME_GPT35 = "gpt-3.5-turbo"
OPENAI_MODEL_NAME_GPT4o = "gpt-4o"
OPENAI_MODEL_NAME_MAP = {
    "openai-gpt-4": OPENAI_MODEL_NAME_GPT4,
    "openai-gpt-35": OPENAI_MODEL_NAME_GPT35,
    "openai-gpt-4o": OPENAI_MODEL_NAME_GPT4o,
}


async_openai_client = AsyncOpenAI(
    http_client=httpx.AsyncClient(
        limits=httpx.Limits(
            max_connections=1000,
            max_keepalive_connections=100
        )
    )
)


@tenacity.retry(wait=tenacity.wait_random_exponential(min=60, max=600), stop=tenacity.stop_after_attempt(10), reraise=True)
async def api_call_single(client: AsyncOpenAI, model: str, messages: list[dict], temperature: float = 0.0, **kwargs):
    # Call the API
    response = await client.chat.completions.create(
        model=model,
        messages=messages,  # Ensure messages is a list
        temperature=temperature,
        **kwargs
    )
    return response

@tenacity.retry(wait=tenacity.wait_random_exponential(min=60, max=600), stop=tenacity.stop_after_attempt(10), reraise=True)
async def api_function_call_single(client: AsyncOpenAI, model: str, messages: list[dict], tools: list[dict], temperature: float = 0.0, **kwargs):
    # Call the API
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        temperature=temperature,
        **kwargs
    )
    return response

async def apply_async(client: AsyncOpenAI, model: str, messages_list: list[list[dict]], **kwargs):
    """
    Apply the OpenAI API asynchronously to a list of messages using high-level asyncio APIs.
    """
    tasks = [api_call_single(client, model, messages, **kwargs) for messages in messages_list]
    results = await asyncio.gather(*tasks)
    return results

async def apply_function_call_async(client: AsyncOpenAI, model: str, messages_list: list[list[dict]], tools: list[dict], **kwargs):
    """
    Apply the OpenAI API asynchronously to a list of messages using high-level asyncio APIs.
    """
    tasks = [api_function_call_single(client, model, messages, tools, **kwargs) for messages in messages_list]
    results = await asyncio.gather(*tasks)
    return results

def batch_call_openai(batch_messages, llm, temperature):
    model = OPENAI_MODEL_NAME_MAP.get(llm)
    if model is not None:
        results = _async_execute(
            async_function = apply_async, 
            client = async_openai_client, 
            model=model, 
            messages_list=batch_messages, 
            temperature=temperature, 
            seed=0
            )
    else:
        raise ValueError(f"Unknown llm: {llm}")
    
    parsed_results = []
    for result in results:
        try:
            content = result.choices[0].message.content
            parsed_results.append(content)
        except:
            parsed_results.append("")
    return parsed_results

def batch_function_call_openai(batch_messages, llm, tools, temperature):
    model = OPENAI_MODEL_NAME_MAP.get(llm)
    if model is not None:
        results = _async_execute(
            async_function = apply_function_call_async, 
            client = async_openai_client, 
            model=model, 
            messages_list=batch_messages, 
            tools=tools, 
            temperature=temperature, 
            seed=0
            )
    else:
        raise ValueError(f"Unknown llm: {llm}")
    parsed_results = []
    for result in results:
        try:
            # parse the outputs
            response_message = result.choices[0].message
            tool_calls = response_message.tool_calls
            outputs = {}
            if tool_calls:
                outputs = json.loads(tool_calls[0].function.arguments)
            parsed_results.append(outputs)
        except:
            parsed_results.append({})
    return parsed_results


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


def prompts_as_chatcompletions_messages(prompts: List[str]):
    """
    chat messages for the OpenAI GPT4 chat completions API
    """
    conversations = []
    for prompt in prompts:
        messages = [{
            "role": "user",
            "content": prompt
        }]
        conversations.append(messages)

    return conversations