# Poke Trello MCP (TypeScript)

A Model Context Protocol (MCP) server exposing Trello tools for Poke.
Built with TypeScript and FastMCP framework.
Deploy on Render with HTTP streaming at /mcp.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/DirectiveCreator/poke-trello-mcp)

## Deployment

### Option 1: One-Click Deploy
Click the "Deploy to Render" button above.

### Option 2: Manual Deployment (Blueprint)
1. Fork this repository
2. Connect your GitHub account to Render
3. Create a new Blueprint on Render
4. Select this repository
5. Render will automatically detect the `render.yaml` configuration

Your server will be available at https://your-service-name.onrender.com/mcp (NOTE THE /mcp).

## Poke Setup (Trello MCP)

You can connect your MCP server to Poke at [poke.com/settings/connections](https://poke.com/settings/connections).

- In Poke, go to Settings → Connections → Integrations → New.
- Add an MCP integration with URL: https://<your-render-service>.onrender.com/mcp
- Once connected, you can call Trello tools via natural prompts or explicit tool usage.
- If Poke seems to cling to an old connection, send `clearhistory` to reset the session.

## Environment variables (set in Render)

Set these in Render (Settings → Environment):
- TRELLO_API_KEY: your Trello API key
- TRELLO_TOKEN: your Trello token
- Optional defaults:
  - TRELLO_BOARD_ID
  - TRELLO_WORKSPACE_ID
- MCP_DEBUG: 0 (set 1 while testing; secrets are never logged)
- ENVIRONMENT: production

## Tools and example prompts

- add_card_to_list — "Add a Trello card called 'Ship v1' to list LIST_ID. Set the description to 'Prepare launch' and the due date to 2025-09-30."
- add_list_to_board — "Create a new list called 'Backlog' on the active Trello board."
- archive_card — "Archive the Trello card with ID CARD_ID."
- archive_list — "Archive the Trello list with ID LIST_ID."
- attach_image_to_card — "Attach IMAGE_URL to the Trello card CARD_ID and name the attachment 'Mockup v2'."
- get_active_board_info — "Show info about the currently active Trello board."
- get_cards_by_list_id — "Show all cards in the Trello list LIST_ID."
- get_lists — "List all lists on the active Trello board." or "List all lists on Trello board BOARD_ID."
- get_my_cards — "Show all Trello cards assigned to me."
- get_recent_activity — "Show the 25 most recent activities on the active Trello board."
- list_boards — "Show all Trello boards I have access to."
- list_boards_in_workspace — "Show all Trello boards in workspace WORKSPACE_ID."
- list_workspaces — "Show all workspaces I have access to."
- move_card — "Move the Trello card CARD_ID to list LIST_ID."
- set_active_board — "Set the active Trello board to BOARD_ID."
- set_active_workspace — "Set the active Trello workspace to WORKSPACE_ID."
- update_card_details — "Rename Trello card CARD_ID to 'Fix crash', set due date to 2025-10-01, and apply labels LABEL_ID1 and LABEL_ID2."
- get_server_info — "Get server info including version and active context."

## Development

### Prerequisites
- Node.js 20+ 
- TypeScript 5+

### Local Setup
```bash
# Install dependencies
npm install

# Copy .env.example to .env and configure
cp .env.example .env

# Run in development mode
npm run dev

# Build for production
npm run build

# Start production server
npm start
```
