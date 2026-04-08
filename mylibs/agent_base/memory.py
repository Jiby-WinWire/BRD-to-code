from langchain_community.chat_message_histories import RedisChatMessageHistory
from azure.search.documents.aio import SearchClient
from datetime import datetime, timedelta
from typing import Optional
import json
from rapidfuzz import fuzz

class MemoryClass:
    def __init__(
        self,
        session_id: str,
        redis_url: str,
        azure_search_client: SearchClient,
    ):
        self.session_id = session_id
        self.redis_url = redis_url
        self.search_client = azure_search_client
        self.short_term_memory = self._init_short_term_memory()
        self.episodic_memory = self._init_episodic_memory()
        self.long_term_memory = self._init_long_term_memory()
        self.semantic_memory = self._init_semantic_memory()

        # Warmup storage
        self.table_descriptions = None
        self.table_schemas = None

    def _init_short_term_memory(self):
        chat_history = RedisChatMessageHistory(
        url=self.redis_url,
        session_id=self.session_id,
        )
        return ShortTermQueryMemory(chat_history)
    
    def _init_episodic_memory(self):
        return RedisChatMessageHistory(
            session_id=self.session_id,
            url=self.redis_url
        )

    def _init_long_term_memory(self):
        return self.search_client

    def _init_semantic_memory(self):
        return self.search_client

    def get_short_term_memory(self):
        return self.short_term_memory

    def get_episodic_memory(self):
        return self.episodic_memory

    def get_long_term_memory(self):
        return self.long_term_memory

    def get_semantic_memory(self):
        return self.semantic_memory

    async def warmup(self, desc_path: str, schema_path: str):
        try:
            self.table_descriptions = await self.load_with_fallback(
                key="table_descriptions",
                fallback_path=desc_path,
                search_text="table descriptions"
            )
        except Exception as e:
            print(f"[Warmup] Failed to load table_descriptions: {e}")
            self.table_descriptions = {}

        try:
            raw_schemas = await self.load_with_fallback(
                key="table_schemas",
                fallback_path=schema_path,
                search_text="table schemas"
            )
        except Exception as e:
            print(f"[Warmup] Failed to load table_schemas: {e}")
            raw_schemas = {}

        unified = {}
        for short_key, entry in raw_schemas.items():
            fq = entry.get("table_name", short_key)
            unified[short_key] = entry
            unified[fq] = entry
        self.table_schemas = unified

    async def load_with_fallback(self, key: str, fallback_path: str, search_text: str):
        try:
            sc = self.get_long_term_memory()
            results = await sc.search(search_text=search_text, query_type=QueryType.SIMPLE, top=1)
            async for result in results:
                content = result.get("content") or result.get("text") or str(result)

                import re
                # Sanitize bad control characters and invalid escapes
                cleaned = re.sub(r'[\x00-\x1F\x7F]', ' ', content)
                cleaned = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', cleaned)

                try:
                    data = json.loads(cleaned)
                except json.JSONDecodeError as je:
                    # print(f"[LongTermMemory] invalid JSON for {key}: {je}")
                    # abort long-term attempt and drop into file fallback
                    break
                self.redis.set(key, json.dumps(data))
                return data
        except Exception as e:
            print(f"[LongTermMemory] Failed to fetch {key}: {e}")
        try:
            with open(fallback_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.redis.set(key, json.dumps(data))
                return data
        except Exception as e:
            print(f"[FallbackFile] Failed to load {key} from disk: {e}")

        return {}

class ShortTermQueryMemory:
    def __init__(self, chat_memory: RedisChatMessageHistory):
        self.chat_memory = chat_memory
        self.expiry_hours = 24
        self.similarity_threshold = 100  # Tune as needed

    async def store_query(self, user_query: str, sql_query: str):
        timestamp = datetime.utcnow().isoformat()
        entry = json.dumps({
            "user_query": user_query,
            "sql_query": sql_query,
            "timestamp": timestamp
        })
        # RedisChatMessageHistory.add_user_message is synchronous, so call it directly
        self.chat_memory.add_user_message(entry)

    async def check_existing_query(self, user_query: str) -> Optional[str]:
        messages = self.chat_memory.messages
        now = datetime.utcnow()
        best_match = None
        best_score = 0

        for msg in messages:
            try:
                content = json.loads(msg.content)
                timestamp = datetime.fromisoformat(content["timestamp"])
                if (now - timestamp) > timedelta(hours=self.expiry_hours):
                    continue

                score = fuzz.token_sort_ratio(content["user_query"], user_query)
                if score > self.similarity_threshold and score > best_score:
                    best_match = content["sql_query"]
                    best_score = score

            except Exception:
                continue

        return best_match
