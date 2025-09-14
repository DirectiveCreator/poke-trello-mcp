#!/usr/bin/env python3
# Poke Trello MCP Server - v1.1.0
import os
import typing as t
import logging
from fastmcp import FastMCP
import httpx
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
import uvicorn

SERVER_NAME = "Trello MCP Server"

# Logging configuration
DEBUG = os.environ.get("MCP_DEBUG", "0").lower() in {"1", "true", "yes"}
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("trello_mcp")

# Suppress noisy MCP errors when not debugging
if not DEBUG:
    # Suppress ClosedResourceError spam from health checks
    logging.getLogger("mcp.server.streamable_http").setLevel(logging.CRITICAL)
    logging.getLogger("mcp.server.streamable_http_manager").setLevel(logging.WARNING)
    # Reduce uvicorn access log noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

TRELLO_BASE_URL = "https://api.trello.com/1"
API_KEY = os.environ.get("TRELLO_API_KEY")
TOKEN = os.environ.get("TRELLO_TOKEN")
ACTIVE_BOARD_ID = os.environ.get("TRELLO_BOARD_ID") or None
ACTIVE_WORKSPACE_ID = os.environ.get("TRELLO_WORKSPACE_ID") or None

mcp = FastMCP(SERVER_NAME)

class TrelloError(Exception):
    pass

class TrelloClient:
    def __init__(self, api_key: str, token: str, base_url: str = TRELLO_BASE_URL, timeout: float = 30.0, debug: bool = False) -> None:
        if not api_key or not token:
            raise TrelloError("Trello API credentials are not configured. Set TRELLO_API_KEY and TRELLO_TOKEN env vars.")
        self.api_key = api_key
        self.token = token
        self.base_url = base_url
        self.debug = debug
        self.client = httpx.Client(base_url=base_url, timeout=timeout)

    def _request(self, method: str, path: str, params: dict | None = None, json: dict | None = None) -> t.Any:
        params = params.copy() if params else {}
        # Add auth
        params.update({"key": self.api_key, "token": self.token})
        url = path if path.startswith("/") else f"/{path}"
        masked = {k: ("***" if k in {"key", "token"} else v) for k, v in params.items()}
        if self.debug:
            logger.debug(f"[Trello] {method} {url} params={masked}")
        resp = self.client.request(method, url, params=params, json=json)
        if self.debug:
            logger.debug(f"[Trello] -> {resp.status_code}")
        try:
            data = resp.json()
        except Exception:
            data = {"text": resp.text}
        if resp.status_code >= 400:
            # Log detailed error body without secrets
            logger.warning(f"[Trello] ERROR {resp.status_code} on {method} {url}: {data}")
            msg = data if isinstance(data, dict) else {"error": data}
            raise TrelloError(f"Trello API error {resp.status_code}: {msg}")
        return data

    # Boards, lists, cards helpers
    def get_board(self, board_id: str) -> dict:
        return self._request("GET", f"/boards/{board_id}", params={"fields": "id,name,url"})

    def list_boards(self) -> list[dict]:
        return self._request("GET", "/members/me/boards", params={"fields": "id,name,url"})

    def list_boards_in_workspace(self, workspace_id: str) -> list[dict]:
        return self._request("GET", f"/organizations/{workspace_id}/boards", params={"fields": "id,name,url"})

    def get_lists(self, board_id: str) -> list[dict]:
        return self._request("GET", f"/boards/{board_id}/lists", params={"fields": "id,name,closed"})

    def add_list_to_board(self, board_id: str, name: str) -> dict:
        # Trello API creates lists via POST /lists with idBoard param
        return self._request("POST", "/lists", params={"name": name, "idBoard": board_id})

    def archive_list(self, list_id: str) -> dict:
        return self._request("PUT", f"/lists/{list_id}/closed", params={"value": "true"})

    def get_cards_by_list(self, list_id: str) -> list[dict]:
        return self._request("GET", f"/lists/{list_id}/cards")

    def add_card_to_list(self, list_id: str, name: str, description: str | None = None, dueDate: str | None = None, labels: list[str] | None = None) -> dict:
        params: dict[str, t.Any] = {"idList": list_id, "name": name}
        if description:
            params["desc"] = description
        if dueDate:
            params["due"] = dueDate
        if labels:
            # Trello expects comma-separated list of label IDs in idLabels
            params["idLabels"] = ",".join(labels)
        return self._request("POST", "/cards", params=params)

    def archive_card(self, card_id: str) -> dict:
        return self._request("PUT", f"/cards/{card_id}/closed", params={"value": "true"})

    def attach_image_to_card(self, card_id: str, image_url: str, name: str | None = None) -> dict:
        params = {"url": image_url}
        if name:
            params["name"] = name
        return self._request("POST", f"/cards/{card_id}/attachments", params=params)

    def move_card(self, card_id: str, list_id: str, pos: str | None = None) -> dict:
        params: dict[str, t.Any] = {"value": list_id}
        data = self._request("PUT", f"/cards/{card_id}/idList", params=params)
        if pos:
            self._request("PUT", f"/cards/{card_id}/pos", params={"value": pos})
        return data

    def update_card_details(self, card_id: str, name: str | None = None, description: str | None = None, dueDate: str | None = None, labels: list[str] | None = None) -> dict:
        params: dict[str, t.Any] = {}
        if name is not None:
            params["name"] = name
        if description is not None:
            params["desc"] = description
        if dueDate is not None:
            params["due"] = dueDate
        if labels is not None:
            params["idLabels"] = ",".join(labels)
        return self._request("PUT", f"/cards/{card_id}", params=params)

    def get_my_cards(self) -> list[dict]:
        return self._request("GET", "/members/me/cards", params={"fields": "id,name,idList,idBoard,url"})

    def get_recent_activity(self, board_id: str, limit: int = 10) -> list[dict]:
        return self._request("GET", f"/boards/{board_id}/actions", params={"limit": limit})

# Instantiate client lazily so server can start without creds during build phase
_client: TrelloClient | None = None

def get_client() -> TrelloClient:
    global _client
    if _client is None:
        # Read fresh env in case they were injected at runtime
        api_key = os.environ.get("TRELLO_API_KEY")
        token = os.environ.get("TRELLO_TOKEN")
        debug = os.environ.get("MCP_DEBUG", "0").lower() in {"1", "true", "yes"}
        _client = TrelloClient(api_key=api_key, token=token, debug=debug)
    return _client

# Maintain active selections in-process (defaults from env)
_active_board_id = ACTIVE_BOARD_ID
_active_workspace_id = ACTIVE_WORKSPACE_ID

@mcp.tool(description="Get information about the MCP server, environment, and active Trello context")
def get_server_info() -> dict:
    logger.info("tool:get_server_info")
    return {
        "server_name": SERVER_NAME,
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "python_version": os.sys.version.split()[0],
        "active_board_id": _active_board_id,
        "active_workspace_id": _active_workspace_id,
    }

@mcp.tool(description="Get info for the currently active board")
def get_active_board_info() -> dict:
    logger.info("tool:get_active_board_info",)
    if not _active_board_id:
        raise TrelloError("No active board set. Provide TRELLO_BOARD_ID or call set_active_board.")
    client = get_client()
    return client.get_board(_active_board_id)

@mcp.tool(description="Fetch all lists on a board. If boardId omitted, uses active board.")
def get_lists(boardId: str | None = None) -> list[dict]:
    logger.info(f"tool:get_lists boardId={boardId or _active_board_id}")
    board = boardId or _active_board_id
    if not board:
        raise TrelloError("No board specified and no active board is set.")
    client = get_client()
    return client.get_lists(board)

@mcp.tool(description="Create a new list on the given or active board")
def add_list_to_board(name: str, boardId: str | None = None) -> dict:
    logger.info(f"tool:add_list_to_board name={name!r} boardId={boardId or _active_board_id}")
    board = boardId or _active_board_id
    if not board:
        raise TrelloError("No board specified and no active board is set.")
    client = get_client()
    return client.add_list_to_board(board, name)

@mcp.tool(description="Archive (close) a Trello list")
def archive_list(listId: str) -> dict:
    logger.info(f"tool:archive_list listId={listId}")
    client = get_client()
    return client.archive_list(listId)

@mcp.tool(description="Fetch cards from a specific list")
def get_cards_by_list_id(listId: str) -> list[dict]:
    logger.info(f"tool:get_cards_by_list_id listId={listId}")
    client = get_client()
    return client.get_cards_by_list(listId)

@mcp.tool(description="Create a Trello card in a list")
def add_card_to_list(listId: str, name: str, description: str | None = None, dueDate: str | None = None, labels: list[str] | None = None) -> dict:
    # Accept camelCase as exposed in schema and map to client internals
    logger.info(f"tool:add_card_to_list listId={listId} name={name!r} dueDate={dueDate} labels_count={(len(labels) if labels else 0)}")
    client = get_client()
    return client.add_card_to_list(list_id=listId, name=name, description=description, dueDate=dueDate, labels=labels)

@mcp.tool(description="Archive (close) a Trello card")
def archive_card(cardId: str) -> dict:
    logger.info(f"tool:archive_card cardId={cardId}")
    client = get_client()
    return client.archive_card(cardId)

@mcp.tool(description="Attach an image URL to a Trello card")
def attach_image_to_card(cardId: str, imageUrl: str, name: str | None = None) -> dict:
    logger.info(f"tool:attach_image_to_card cardId={cardId} imageUrl_len={len(imageUrl)} name={name!r}")
    client = get_client()
    return client.attach_image_to_card(card_id=cardId, image_url=imageUrl, name=name)

@mcp.tool(description="Move a card to another list on the same board")
def move_card(cardId: str, listId: str, pos: str | None = None) -> dict:
    logger.info(f"tool:move_card cardId={cardId} listId={listId} pos={pos}")
    client = get_client()
    return client.move_card(card_id=cardId, list_id=listId, pos=pos)

@mcp.tool(description="Update card details: name, description, dueDate, labels")
def update_card_details(cardId: str, name: str | None = None, description: str | None = None, dueDate: str | None = None, labels: list[str] | None = None) -> dict:
    logger.info(f"tool:update_card_details cardId={cardId} name={name!r} dueDate={dueDate} labels_count={(len(labels) if labels else 0)}")
    client = get_client()
    return client.update_card_details(card_id=cardId, name=name, description=description, dueDate=dueDate, labels=labels)

@mcp.tool(description="List boards accessible to the Trello user")
def list_boards() -> list[dict]:
    logger.info("tool:list_boards")
    client = get_client()
    return client.list_boards()

@mcp.tool(description="List boards in a given workspace (organization)")
def list_boards_in_workspace(workspaceId: str) -> list[dict]:
    logger.info(f"tool:list_boards_in_workspace workspaceId={workspaceId}")
    client = get_client()
    return client.list_boards_in_workspace(workspaceId)

@mcp.tool(description="Fetch all cards assigned to the current user")
def get_my_cards() -> list[dict]:
    logger.info("tool:get_my_cards")
    client = get_client()
    return client.get_my_cards()

@mcp.tool(description="Fetch recent activity (actions) on a board. If boardId omitted, uses active board.")
def get_recent_activity(limit: int = 10, boardId: str | None = None) -> list[dict]:
    logger.info(f"tool:get_recent_activity limit={limit} boardId={boardId or _active_board_id}")
    board = boardId or _active_board_id
    if not board:
        raise TrelloError("No board specified and no active board is set.")
    client = get_client()
    return client.get_recent_activity(board_id=board, limit=limit)

@mcp.tool(description="Set the active board for subsequent operations")
def set_active_board(boardId: str) -> dict:
    logger.info(f"tool:set_active_board boardId={boardId}")
    global _active_board_id
    _active_board_id = boardId
    # return basic info for confirmation
    client = get_client()
    return {"active_board": client.get_board(boardId)}

@mcp.tool(description="Set the active workspace (organization) for subsequent operations")
def set_active_workspace(workspaceId: str) -> dict:
    logger.info(f"tool:set_active_workspace workspaceId={workspaceId}")
    global _active_workspace_id
    _active_workspace_id = workspaceId
    return {"active_workspace_id": _active_workspace_id}

# Create health endpoint
async def health(request):
    return JSONResponse({"status": "ok", "name": SERVER_NAME, "endpoint": "/mcp"})

# Create the ASGI app with health endpoint and MCP
def create_app():
    """Create the ASGI application with health endpoint."""
    # Get the MCP ASGI app
    mcp_asgi = mcp.get_asgi_app(transport="http", stateless_http=True)
    
    # Create Starlette app with health route and mount MCP
    app = Starlette(routes=[
        Route("/", health),
        Route("/health", health),
        Mount("/", app=mcp_asgi),  # MCP handles /mcp internally
    ])
    return app

# Export for uvicorn
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    logger.info(f"Starting {SERVER_NAME} on {host}:{port} | Health: / and /health | SSE: /mcp | DEBUG={DEBUG}")
    uvicorn.run(app, host=host, port=port)
