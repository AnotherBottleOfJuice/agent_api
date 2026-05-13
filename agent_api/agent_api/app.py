from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import APIKeyHeader
from fastapi.openapi.utils import get_openapi
import os
from dotenv import load_dotenv
import uuid
from dataclasses import replace

from database import DatabaseHandler

from .generate import make_completion
from .api_types import CreateCompletion, UpdateCompletion, LLMConfig, MCP, as_json
from .api_exceptions import LLMException

load_dotenv()

app = FastAPI()
database_handler = DatabaseHandler('api_agent.db')
SECRET_KEY = os.getenv('SECRET_KEY')
DEFAULT_MCP_URL = os.getenv('DEFAULT_MCP_URL')
DEFAULT_MCP_TOKEN = os.getenv('DEFAULT_MCP_TOKEN')
DEFAULT_MCP_NAME = os.getenv('DEFAULT_MCP_NAME')

database_handler.connect()

admin_key_scheme = APIKeyHeader(name="X-Admin-Key", auto_error=False, scheme_name="AdminKeyAuth")
user_token_scheme = APIKeyHeader(name="X-User-Token", auto_error=False, scheme_name="UserTokenAuth")

async def get_current_user(user_token: str = Depends(user_token_scheme)):
    if not user_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing")
    try:
        user_id = database_handler.validate_user_token(user_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return user_id

@app.post("/admin/add_user", status_code=status.HTTP_201_CREATED)
async def add_user(key: str = Depends(admin_key_scheme)):
    if key != SECRET_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    user_token = str(uuid.uuid4())
    database_handler.add_user(user_token)

    try:
        user_id = database_handler.validate_user_token(user_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")

    default_mcp_id = await add_mcp(
        MCP(
            name=DEFAULT_MCP_NAME,
            url=DEFAULT_MCP_URL,
            token=DEFAULT_MCP_TOKEN
        ),
        uid=user_id
    )

    return {
        "status": "success",
        "operation": "add_user",
        "user_id": user_id,
        "user_token": user_token,
        "default_mcp_id": default_mcp_id,
    }

@app.post('/v1/chat/completions', status_code=status.HTTP_201_CREATED)
async def create_chat_completion(
        request: CreateCompletion,
        uid: str = Depends(get_current_user)
    ):
    try:
        llm_config = database_handler.get_llm_config(uid, request.llm_config_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    mcps = {}
    try:
        for mcp_id in request.mcp_ids:
            mcp = database_handler.get_mcp(uid, mcp_id)
            mcps[mcp_id] = mcp
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    try:
        completion = await make_completion(request.completion, llm_config, mcps)
    except LLMException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    try:
        completion_id = database_handler.add_completion(
            uid,
            as_json(completion),
            request.llm_config_id,
            request.mcp_ids
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return {
        "status": "success",
        "operation": "add_completion",
        "completion_id": completion_id,
        "llm_config_id": request.llm_config_id,
        "mcp_ids": request.mcp_ids,
    }

@app.put('/v1/chat/completions/{completion_id}')
async def update_chat_completion(
        completion_id: int,
        request: UpdateCompletion,
        uid: str = Depends(get_current_user)
    ):
    try:
        completion, llm_config_id, mcps = database_handler.get_completion_with_config(uid, completion_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if request.completion is not None:
        completion.messages.extend(request.completion.messages)

    if request.llm_config_id is not None:
        try:
            llm_config_id = database_handler.get_llm_config(uid, request.llm_config_id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if request.mcp_ids_to_add is not None:
        try:
            for mcp_id in request.mcp_ids_to_add:
                mcp = database_handler.get_mcp(uid, mcp_id)
                mcps[mcp_id] = mcp
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if request.mcp_ids_to_remove is not None:
        try:
            for mcp_id in request.mcp_ids_to_remove:
                mcp = database_handler.get_mcp(uid, mcp_id)
                mcps.pop(mcp_id, None)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    try:
        completion = await make_completion(
            completion,
            database_handler.get_llm_config(uid, llm_config_id),
            mcps
        )
    except LLMException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    try:
        database_handler.update_completion(
            uid, completion_id,
            as_json(completion),
            llm_config_id,
            list(mcps.keys())
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return {
        "status": "success",
        "operation": "update_completion",
        "completion_id": completion_id,
        "llm_config": database_handler.get_llm_config(uid, llm_config_id),
        "mcps": mcps,
    }

@app.get('/v1/chat/completions')
async def get_completions(uid: str = Depends(get_current_user)):
    try:
        return database_handler.get_user_completions(uid)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get('/v1/chat/completions/{completion_id}')
async def get_chat_completion(completion_id: int, uid: str = Depends(get_current_user)):
    try:
        completion, llm_config_id, mcps = database_handler.get_completion_with_config(uid, completion_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return {
        "status": "success",
        "operation": "get_completion",
        "completion_id": completion_id,
        "completion": completion,
        "llm_config": database_handler.get_llm_config(uid, llm_config_id),
        "mcps": mcps,
    }

@app.delete('/v1/chat/completions/{completion_id}')
async def delete_completion(completion_id: int, uid: str = Depends(get_current_user)):
    try:
        database_handler.delete_completion(uid, completion_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return {"message": "Completion deleted successfully."}

@app.post('/v1/chat/llm/', status_code=status.HTTP_201_CREATED)
async def add_llm_config(llm_config : LLMConfig, uid: str = Depends(get_current_user)):
    try:
        config_id = database_handler.add_llm_config(uid, llm_config)
        return {
            "status": "success",
            "operation": "add_llm_config",
            "llm_config_id": config_id,
            "config_name": llm_config.config_name,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get('/v1/chat/llm/', status_code=status.HTTP_200_OK)
async def get_llm_configs(uid: str = Depends(get_current_user)):
    try:
        llm_configs = database_handler.get_user_llm_configs(uid)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return {
        "status": "success",
        "operation": "get_llm_configs",
        "llm_configs": llm_configs,
    }

@app.post('/v1/chat/mcp', status_code=status.HTTP_201_CREATED)
async def add_mcp(mcp : MCP, uid: str = Depends(get_current_user)):
    try:
        mcp_id = database_handler.add_mcp(uid, mcp)
        return {
            "status": "success",
            "operation": "add_mcp",
            "mcp_id": mcp_id,
            "name": mcp.name,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get('/v1/chat/mcp')
async def get_mcps(uid: str = Depends(get_current_user)):
    try:
        mcps = database_handler.get_user_mcps(uid)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return {
        "status": "success",
        "operation": "get_mcps",
        "mcps": [
            replace(database_handler.get_mcp(uid, mcp_id), token=None)
            for mcp_id in mcps
        ],
    }
