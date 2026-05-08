import re
import json
from dataclasses import is_dataclass, asdict

from openai import AsyncOpenAI
from openai.types.chat.chat_completion import Choice

from .mcp_utils import MCPHandler
from .api_types import ChatCompletion, LLMConfig, MCP, Message
from .api_exceptions import LLMException

def _sanitize_tool_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)[:64]

def _message_to_param(message):
    if isinstance(message, dict):
        return message
    if is_dataclass(message):
        return asdict(message)
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)
    raise TypeError(f"Unsupported message type: {type(message)}")

async def generate_response(
        completion: ChatCompletion,
        llm_config: LLMConfig,
        mcps: dict[int, MCP]
        ):
    client = AsyncOpenAI(
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
    )

    tools = []
    for mcp_id, mcp in mcps.items():
        for tool in await MCPHandler(mcp).get_tools():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": _sanitize_tool_name(f"{mcp_id}__{tool.name}"),
                        "description": tool.description or "",
                        "parameters": tool.inputSchema,
                    },
                }
            )

    request_params = {
        "messages": [_message_to_param(message) for message in completion.messages],
        "model": llm_config.model,
    }
    if tools:
        request_params["tools"] = tools
    return await client.chat.completions.create(**request_params)

async def make_completion(
        completion : ChatCompletion,
        llm_config : LLMConfig,
        mcps: dict[int, MCP]
        ):

    last_tool_call = None

    for _ in range(10):
        response = await generate_response(completion, llm_config, mcps)

        choice : Choice = response.choices[0]

        md = choice.message.model_dump(exclude_none=True)
        completion.messages.append(
            Message(role=md.get("role"),
                    content=md.get("content"),
                    tool_calls=md.get("tool_calls", None)
            ))

        if choice.finish_reason == "stop":
            break

        for tool_call in choice.message.tool_calls:
            if tool_call.id == last_tool_call:
                raise LLMException("LLM is stuck in a loop calling the same tool without making progress")

            last_tool_call = tool_call.id

            mcp_id, tool_name = tool_call.function.name.split('__')

            result = await MCPHandler(
                    mcp_config=mcps[int(mcp_id)]
                ).call_tool(tool_name=tool_name, message=json.loads(tool_call.function.arguments))

            completion.messages.append(
                Message(
                    role="tool",
                    tool_call_id=tool_call.id,
                    content=result.content
                ))
    else:
        raise LLMException("Maximum iterations reached")

    return completion
