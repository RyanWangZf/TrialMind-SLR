import httpx
from openai import OpenAI
from openai import AzureOpenAI
import tenacity
OPENAI_MODEL_NAME_GPT4 = "gpt-4-turbo"  # new gpt-4-turbo
OPENAI_MODEL_NAME_GPT35 = "gpt-3.5-turbo"
OPENAI_MODEL_NAME_GPT4o = "gpt-4o"
OPENAI_MODEL_NAME_MAP = {
    "openai-gpt-4": OPENAI_MODEL_NAME_GPT4,
    "openai-gpt-35": OPENAI_MODEL_NAME_GPT35,
    "openai-gpt-4o": OPENAI_MODEL_NAME_GPT4o,
}

openai_client = OpenAI(
    http_client=httpx.Client(
        limits=httpx.Limits(
            max_connections=1000,
            max_keepalive_connections=100
        )
    )
)

@tenacity.retry(wait=tenacity.wait_random_exponential(min=1, max=5), stop=tenacity.stop_after_attempt(10), reraise=True)
def api_call_single(client: OpenAI, model: str, messages: list[dict], temperature: float = 0.0, **kwargs):
    # Call the API
    response = client.chat.completions.create(
        model=model,
        messages=messages,  # Ensure messages is a list
        temperature=temperature,
        **kwargs
    )
    return response

@tenacity.retry(wait=tenacity.wait_random_exponential(min=1, max=5), stop=tenacity.stop_after_attempt(10), reraise=True)
def api_function_call_single(client: OpenAI, model: str, messages: list[dict], tools: list[dict], temperature: float = 0.0, **kwargs):
    # Call the API
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        temperature=temperature,
        **kwargs
    )
    return response

def call_openai(llm: str, messages: list[dict], temperature: float = 0.0, **kwargs):
    """
    Call the OpenAI API asynchronously to a list of messages using high-level asyncio APIs.
    """
    model = OPENAI_MODEL_NAME_MAP.get(llm)
    if model is None:
        raise ValueError(f"Unsupported LLM model: {llm}")
    response = api_call_single(openai_client, model, messages, temperature, **kwargs)
    return response