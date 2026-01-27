"""示例"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from src.claude_code import ConversationClient


async def test():
    async with ConversationClient(session_id="389402db-7348-46c4-9085-da86dc559a89") as client:
        r = await client.chat("我们之前聊过什么？")
        print(f"Claude: {r.content}\n")


async def main():
    async with ConversationClient() as client:
        r1 = await client.chat("用一句话解释递归")
        print(f"Claude: {r1.content}\n")

        r2 = await client.chat("给个例子")
        print(f"Claude: {r2.content}\n")

        print(f"Session ID: {client.session_id}")


if __name__ == "__main__":
    asyncio.run(test())
