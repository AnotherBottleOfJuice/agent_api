from dataclasses import dataclass, asdict, is_dataclass
import json
from typing import Any, Optional, Literal, List


def _to_jsonable(value):
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return value.model_dump(exclude_none=True)
    return value

def as_json(content):
    return json.dumps(_to_jsonable(content))

@dataclass
class LLMConfig:
    config_name: str
    model: str
    api_key: str
    base_url: str

@dataclass
class MCP:
    name: str
    url: str
    token: str

@dataclass
class Message:
    role: Literal["user", "assistant", "system", "tool"]
    content: Optional[Any] = None
    tool_calls: Optional[List[Any]] = None
    tool_call_id: Optional[str] = None

@dataclass
class ChatCompletion:
    messages: List[Message]

@dataclass
class CreateCompletion:
    completion: ChatCompletion
    llm_config_id: int
    mcp_ids: List[int]

@dataclass
class UpdateCompletion:
    completion: Optional[ChatCompletion] = None
    llm_config_id: Optional[int] = None
    mcp_ids_to_add: Optional[List[int]] = None
    mcp_ids_to_remove: Optional[List[int]] = None



__all__ = [
    'LLMConfig', 
    'MCP', 
    'Message', 
    'ChatCompletion', 
    'CreateCompletion', 
    'UpdateCompletion'
]