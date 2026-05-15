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


async def make_completion(
        completion : ChatCompletion,
        llm_config : LLMConfig,
        mcps: dict[int, MCP]
        ):
    
    client = AsyncOpenAI(
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
    )

    available_tools = []
    tool_to_mcp = {}
    tool_to_original_name = {}

    for mcp_id, mcp in mcps.items():
        for tool in await MCPHandler(mcp).get_tools():
            s_name = _sanitize_tool_name(tool.name)
            tool_to_mcp[s_name] = mcp_id
            tool_to_original_name[s_name] = tool.name
            available_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": s_name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema,
                    },
                }
            )

    last_tool_call = None
    cnt_duplicate_tool_calls = 0

    for _ in range(10): 
        request_params = {
            "messages": [_message_to_param(message) for message in completion.messages],
            "model": llm_config.model,
        }
        if available_tools:
            request_params["tools"] = available_tools

        response = await client.chat.completions.create(**request_params)
        choice : Choice = response.choices[0]

        md = choice.message.model_dump(exclude_none=True)
        completion.messages.append(
            Message(role=md.get("role"),
                    content=md.get("content"),
                    tool_calls=md.get("tool_calls", None)
            ))

        if choice.finish_reason == "stop" or not getattr(choice.message, "tool_calls", None):
            break

        for tool_call in choice.message.tool_calls:
            s_name = tool_call.function.name
            
            if s_name == last_tool_call:
                cnt_duplicate_tool_calls += 1
                if cnt_duplicate_tool_calls >= 3:
                    raise LLMException("LLM is stuck in a loop calling the same tool without making progress")
            else:
                cnt_duplicate_tool_calls = 1

            last_tool_call = s_name

            if s_name not in tool_to_mcp:
                raise LLMException(f"LLM tried to call unknown tool: {s_name}")
                
            mcp_id = tool_to_mcp[s_name]
            tool_name = tool_to_original_name[s_name]

            result = await MCPHandler(
                    mcp_config=mcps[mcp_id]
                ).call_tool(tool_name=tool_name, message=json.loads(tool_call.function.arguments))

            content_str = ""
            if hasattr(result, "content") and isinstance(result.content, list):
                out = []
                for c in result.content:
                    if getattr(c, "type", "") == "text" and hasattr(c, "text"):
                        out.append(c.text)
                    else:
                        out.append(str(c))
                content_str = "\n".join(out)
            else:
                content_str = str(getattr(result, "content", result))
                
            if getattr(result, "isError", False):
                content_str = f"Error: {content_str}"

            completion.messages.append(
                Message(
                    role="tool",
                    tool_call_id=tool_call.id,
                    content=content_str
                ))
    else:
        raise LLMException("Maximum iterations reached")

    return completion
