import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from groq import AsyncGroq
from fastmcp import Client
from fastmcp.client.auth import OAuth
from key_value.aio.stores.disk import DiskStore

URL = "https://expense-tracker-mcp-serve.fastmcp.app/mcp"
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")          # use any current tool-capable Groq model
HIDDEN_TOOLS = {"clear_all_expenses", "delete_expense"}   # not exposed to the model
MAX_STEPS = 6

SYSTEM = (
    "You are an expense tracking assistant. Use the tools to add, view and "
    "analyze expenses. If a required field is missing, ask the user. "
    "Today's date is 2026-10-25. Keep replies short."
)

llm = AsyncGroq()          # reads GROQ_API_KEY
sessions: dict[str, list] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    auth = OAuth(
        mcp_url=URL,
        token_storage=DiskStore(directory=os.path.expanduser("~/.expense_client_tokens")),
    )
    async with Client(URL, auth=auth) as mcp:
        listed = await mcp.list_tools()
        app.state.mcp = mcp
        app.state.tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": getattr(t, "input_schema", None) or t.inputSchema,
                },
            }
            for t in listed
            if t.name not in HIDDEN_TOOLS
        ]
        print(f"Connected. {len(app.state.tools)} tools available.")
        yield


app = FastAPI(lifespan=lifespan)


class ChatIn(BaseModel):
    session_id: str
    message: str


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/chat")
async def chat(body: ChatIn):
    mcp = app.state.mcp
    messages = sessions.setdefault(body.session_id, [{"role": "system", "content": SYSTEM}])
    messages.append({"role": "user", "content": body.message})

    try:
        for _ in range(MAX_STEPS):
            resp = await llm.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=app.state.tools,
                tool_choice="auto",
                max_tokens=1000,
            )
            msg = resp.choices[0].message

            if not msg.tool_calls:
                messages.append({"role": "assistant", "content": msg.content or ""})
                return {"reply": msg.content or ""}

            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })

            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                    out = await mcp.call_tool(tc.function.name, args)
                    text = "".join(getattr(c, "text", "") for c in out.content) or str(out.data)
                except Exception as e:
                    text = f"Error: {e}"
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": text})

        return {"reply": "Sorry, that took too many steps. Please try rephrasing."}
    except Exception as e:
        return {"reply": f"Server error: {e}"}
