import asyncio
from fastmcp import Client

URL = "https://expense-tracker-mcp-serve.fastmcp.app/mcp"

async def main():
    async with Client(URL, auth="oauth") as client:
        tools = await client.list_tools()
        print(f"Connected. {len(tools)} tools found:\n")
        for t in tools:
            print(f"- {t.name}: {list(t.inputSchema.get('properties', {}).keys())}")

        result = await client.call_tool("get_expenses", {})
        print("\nExpenses:", result.data)

asyncio.run(main())