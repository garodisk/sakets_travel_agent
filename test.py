import asyncio
import json
import rich
from mcp_client_test import tavily_mcp_search

if __name__ == "__main__":
    query = "Latest AI news"

    result = asyncio.run(tavily_mcp_search(query))

    text = result[0]["text"]
    data = json.loads(text)

    rich.print_json(data=data)