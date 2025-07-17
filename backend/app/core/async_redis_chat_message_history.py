import json
import redis.asyncio as redis
from typing import List, Sequence
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict

class AsyncRedisChatMessageHistory:
    """Chat message history stored in a Redis database."""

    def __init__(self, session_id: str, url: str = "redis://localhost:6379/0", key_prefix: str = "message_store:"):
        self.redis_client = redis.from_url(url)
        self.session_id = session_id
        self.key = key_prefix + session_id

    async def aget_messages(self) -> List[BaseMessage]:
        """Retrieve messages from Redis."""
        _items = await self.redis_client.lrange(self.key, 0, -1)
        items = [json.loads(m.decode("utf-8")) for m in _items]
        messages = messages_from_dict(items)
        return messages

    async def aadd_messages(self, messages: Sequence[BaseMessage]) -> None:
        """Append messages to the history in Redis."""
        for message in messages:
            await self.redis_client.rpush(self.key, json.dumps(message_to_dict(message)))

    async def aclear(self) -> None:
        """Clear session memory from Redis."""
        await self.redis_client.delete(self.key)
