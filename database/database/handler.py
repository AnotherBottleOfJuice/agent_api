import json
import sqlite3
from datetime import datetime, timezone

from api_agent.api_agent.api_types import LLMConfig, MCP, ChatCompletion


class DatabaseHandler:
    def __init__(self, db_name):
        self.db_name = db_name
        self.connection: sqlite3.Connection = None

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_name)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _create_json_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            '''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS llm_config (
                config_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                payload TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS mcp (
                mcp_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                payload TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS completions (
                completion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                payload TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE UNIQUE INDEX IF NOT EXISTS ndx_users_token
                ON users(json_extract(payload, '$.user_token'));

            CREATE UNIQUE INDEX IF NOT EXISTS ndx_llm_user_config_name
                ON llm_config(user_id, json_extract(payload, '$.config_name'));

            CREATE UNIQUE INDEX IF NOT EXISTS ndx_mcp_user_name
                ON mcp(user_id, json_extract(payload, '$.name'));

            CREATE INDEX IF NOT EXISTS ndx_mcp_user_id ON mcp(user_id);
            CREATE INDEX IF NOT EXISTS ndx_llm_user_id ON llm_config(user_id);
            CREATE INDEX IF NOT EXISTS ndx_completion_user_id ON completions(user_id);
            '''
        )

    def connect(self):
        with self._connect() as conn:
            self._create_json_schema(conn)

    def close(self):
        if self.connection:
            self.connection.close()

    def add_user(self, user_token):
        try:
            with self._connect() as conn:
                payload = json.dumps({"user_token": user_token, "created_at": self._now_iso()})
                conn.execute(
                    'INSERT INTO users (payload) VALUES (?)',
                    (payload,)
                )
        except sqlite3.IntegrityError:
            raise ValueError("Token already exists")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id FROM users WHERE json_extract(payload, '$.user_token') = ?",
                (user_token,),
            ).fetchone()
            if not row:
                raise ValueError("Token not found after insert")
            return row[0]

    def add_mcp(self, user_id, mcp : MCP):
        with self._connect() as conn:
            payload = json.dumps({
                "name": mcp.name,
                "url": mcp.url,
                "token": mcp.token,
                "created_at": self._now_iso(),
            })
            cursor = conn.execute(
                'INSERT INTO mcp (user_id, payload) VALUES (?, ?)',
                (user_id, payload),
            )
            return cursor.lastrowid

    def add_llm_config(self, user_id, llm_config : LLMConfig):
        with self._connect() as conn:
            payload = json.dumps({
                "config_name": llm_config.config_name,
                "model": llm_config.model,
                "api_key": llm_config.api_key,
                "base_url": llm_config.base_url,
                "created_at": self._now_iso(),
            })
            cursor = conn.execute(
                'INSERT INTO llm_config (user_id, payload) VALUES (?, ?)',
                (user_id, payload),
            )
            return cursor.lastrowid

    def add_completion(self, user_id, completion_json, llm_config_id, mcp_ids):
        with self._connect() as conn:
            llm_exists = conn.execute(
                'SELECT config_id FROM llm_config WHERE config_id = ? AND user_id = ?',
                (llm_config_id, user_id),
            ).fetchone()
            if not llm_exists:
                raise ValueError("LLM config not found or access denied")

            payload = json.dumps({
                "completion_json": completion_json,
                "llm_config_id": llm_config_id,
                "mcp_ids": list(mcp_ids),
                "created_at": self._now_iso(),
            })
            cursor = conn.execute(
                'INSERT INTO completions (user_id, payload) VALUES (?, ?)',
                (user_id, payload),
            )
            return cursor.lastrowid

    def delete_completion(self, user_id, completion_id):
        with self._connect() as conn:
            result = conn.execute(
                'SELECT completion_id FROM completions WHERE completion_id = ? AND user_id = ?',
                (completion_id, user_id)
            ).fetchone()

            if not result:
                raise ValueError("Completion not found or access denied")

            conn.execute(
                'DELETE FROM completions WHERE completion_id = ? AND user_id = ?',
                (completion_id, user_id)
            )

    def add_mcp_to_completion(self, user_id, mcp_id, completion_id):
        with self._connect() as conn:
            completion_row = conn.execute(
                'SELECT payload FROM completions WHERE completion_id = ? AND user_id = ?',
                (completion_id, user_id)
            ).fetchone()

            if not completion_row:
                raise ValueError("Completion not found or access denied")

            mcp = conn.execute(
                'SELECT mcp_id FROM mcp WHERE mcp_id = ? AND user_id = ?',
                (mcp_id, user_id)
            ).fetchone()

            if not mcp:
                raise ValueError("MCP not found or access denied")

            payload = json.loads(completion_row[0])
            mcp_ids = payload.get("mcp_ids", [])
            if mcp_id not in mcp_ids:
                mcp_ids.append(mcp_id)
            payload["mcp_ids"] = mcp_ids

            conn.execute(
                'UPDATE completions SET payload = ? WHERE completion_id = ? AND user_id = ?',
                (json.dumps(payload), completion_id, user_id),
            )

    def get_completion_with_config(self, user_id, completion_id):
        with self._connect() as conn:
            completion_row = conn.execute(
                'SELECT payload FROM completions WHERE completion_id = ? AND user_id = ?',
                (completion_id, user_id),
            ).fetchone()

            if not completion_row:
                raise ValueError("Completion not found or access denied")

            completion_payload = json.loads(completion_row[0])
            llm_config_id = completion_payload.get("llm_config_id")
            llm_row = conn.execute(
                'SELECT payload FROM llm_config WHERE config_id = ? AND user_id = ?',
                (llm_config_id, user_id),
            ).fetchone()
            if not llm_row:
                raise ValueError("LLM config not found or access denied")

            mcp_ids = completion_payload.get("mcp_ids", [])
            mcps = {}
            for mcp_id in mcp_ids:
                mcp_row = conn.execute(
                    'SELECT payload FROM mcp WHERE mcp_id = ? AND user_id = ?',
                    (mcp_id, user_id),
                ).fetchone()
                if mcp_row:
                    mcp_payload = json.loads(mcp_row[0])
                    mcps[mcp_payload.get("name", "")] = MCP(
                        name=mcp_payload.get("name", ""),
                        url=mcp_payload.get("url", ""),
                        token=mcp_payload.get("token", ""),
                    )

        completion_json = completion_payload.get("completion_json", "{\"messages\": []}")
        completion_data = json.loads(completion_json)
        messages = completion_data.get("messages", []) if isinstance(completion_data, dict) else completion_data

        return (
            ChatCompletion(messages=messages),
            llm_config_id,
            mcps,
        )

    def validate_user_token(self, user_token):
        with self._connect() as conn:
            result = conn.execute(
                "SELECT user_id FROM users WHERE json_extract(payload, '$.user_token') = ?",
                (user_token,),
            ).fetchone()

        if not result:
            raise ValueError("Invalid token")

        return result[0]

    def get_llm_config(self, user_id, llm_config_id):
        with self._connect() as conn:
            result = conn.execute(
                'SELECT payload FROM llm_config WHERE config_id = ? AND user_id = ?',
                (llm_config_id, user_id),
            ).fetchone()

        if not result:
            raise ValueError("LLM config not found or access denied")

        payload = json.loads(result[0])

        return LLMConfig(
            config_name=payload.get("config_name", ""),
            model=payload.get("model", ""),
            api_key=payload.get("api_key", ""),
            base_url=payload.get("base_url", ""),
        )

    def get_mcp(self, user_id, mcp_id):
        with self._connect() as conn:
            result = conn.execute(
                'SELECT payload FROM mcp WHERE mcp_id = ? AND user_id = ?',
                (mcp_id, user_id),
            ).fetchone()

        if not result:
            raise ValueError("MCP not found or access denied")

        payload = json.loads(result[0])

        return MCP(
            name=payload.get("name", ""),
            url=payload.get("url", ""),
        )

    def get_user_completions(self, user_id):
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT completion_id, payload FROM completions WHERE user_id = ? ORDER BY completion_id DESC',
                (user_id,),
            ).fetchall()

        result = []
        for completion_id, payload_raw in rows:
            payload = json.loads(payload_raw)
            result.append(
                {
                    "completion_id": completion_id,
                    "llm_config_id": payload.get("llm_config_id"),
                    "mcp_ids": payload.get("mcp_ids", []),
                    "created_at": payload.get("created_at"),
                }
            )
        return result

    def get_user_mcps(self, user_id):
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT mcp_id FROM mcp WHERE user_id = ? ORDER BY mcp_id DESC',
                (user_id,),
            ).fetchall()
        return [row[0] for row in rows]

    def get_user_llm_configs(self, user_id):
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT config_id, payload FROM llm_config WHERE user_id = ? ORDER BY config_id DESC',
                (user_id,),
            ).fetchall()

        result = []
        for config_id, payload_raw in rows:
            payload = json.loads(payload_raw)
            result.append(
                {
                    "config_id": config_id,
                    "config_name": payload.get("config_name"),
                    "model": payload.get("model"),
                    "created_at": payload.get("created_at"),
                }
            )
        return result

    def update_completion(self, user_id, completion_id, completion_json, llm_config_id, mcp_ids):
        with self._connect() as conn:
            result = conn.execute(
                'SELECT completion_id, payload FROM completions WHERE completion_id = ? AND user_id = ?',
                (completion_id, user_id)
            ).fetchone()

            if not result:
                raise ValueError("Completion not found or access denied")

            payload = json.dumps({
                "completion_json": completion_json,
                "llm_config_id": llm_config_id,
                "mcp_ids": mcp_ids,
                "created_at": json.loads(result[1]).get("created_at", self._now_iso()),
                "updated_at": self._now_iso(),
            })

            conn.execute(
                'UPDATE completions SET payload = ? WHERE completion_id = ? AND user_id = ?',
                (payload, completion_id, user_id)
            )

