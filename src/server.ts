#!/usr/bin/env node
// Poke Trello MCP Server - v2.0.0 (TypeScript)
import { FastMCP } from 'fastmcp';
import { z } from 'zod';

const SERVER_NAME = 'Trello MCP Server';
const TRELLO_BASE_URL = 'https://api.trello.com/1';
// Environment configuration
const API_KEY = process.env.TRELLO_API_KEY;
const TOKEN = process.env.TRELLO_TOKEN;
const DEBUG = ['1', 'true', 'yes'].includes(process.env.MCP_DEBUG?.toLowerCase() || '0');

// Active selections (defaults from env)
let activeBoard: string | undefined = process.env.TRELLO_BOARD_ID;
let activeWorkspace: string | undefined = process.env.TRELLO_WORKSPACE_ID;

// Initialize FastMCP server
const server = new FastMCP({
  name: SERVER_NAME,
  version: '2.0.0',
});

// Custom error class
class TrelloError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'TrelloError';
  }
}

// Trello API client
class TrelloClient {
  private apiKey: string;
  private token: string;
  private baseUrl: string;
  private debug: boolean;

  constructor(apiKey: string | undefined, token: string | undefined, baseUrl = TRELLO_BASE_URL, debug = false) {
    if (!apiKey || !token) {
      throw new TrelloError('Trello API credentials are not configured. Set TRELLO_API_KEY and TRELLO_TOKEN env vars.');
    }
    this.apiKey = apiKey;
    this.token = token;
    this.baseUrl = baseUrl;
    this.debug = debug;
  }

  private async request<T = any>(method: string, path: string, params?: Record<string, any>, json?: Record<string, any>): Promise<T> {
    const url = new URL(path.startsWith('/') ? path : `/${path}`, this.baseUrl);
    
    // Add auth params
    url.searchParams.append('key', this.apiKey);
    url.searchParams.append('token', this.token);
    
    // Add additional params
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    if (this.debug) {
      const maskedUrl = url.toString().replace(this.apiKey, '***').replace(this.token, '***');
      console.log(`[Trello] ${method} ${maskedUrl}`);
    }

    const options: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    if (json) {
      options.body = JSON.stringify(json);
    }

    const response = await fetch(url.toString(), options);
    
    if (this.debug) {
      console.log(`[Trello] -> ${response.status}`);
    }

    // Read the response body once and store it
    const responseText = await response.text();
    let data: any;
    
    try {
      // Try to parse as JSON
      data = responseText ? JSON.parse(responseText) : {};
    } catch (e) {
      // If not JSON, return as text object
      data = { text: responseText };
    }

    if (!response.ok) {
      console.warn(`[Trello] ERROR ${response.status} on ${method} ${path}: ${JSON.stringify(data)}`);
      throw new TrelloError(`Trello API error ${response.status}: ${JSON.stringify(data)}`);
    }

    return data;
  }

  // Board operations
  async getBoard(boardId: string) {
    return this.request('GET', `/boards/${boardId}`, { fields: 'id,name,url' });
  }

  async listBoards() {
    return this.request('GET', '/members/me/boards', { fields: 'id,name,url' });
  }

  async listBoardsInWorkspace(workspaceId: string) {
    return this.request('GET', `/organizations/${workspaceId}/boards`, { fields: 'id,name,url' });
  }

  // List operations
  async getLists(boardId: string) {
    return this.request('GET', `/boards/${boardId}/lists`, { fields: 'id,name,closed' });
  }

  async addListToBoard(boardId: string, name: string) {
    return this.request('POST', '/lists', { name, idBoard: boardId });
  }

  async archiveList(listId: string) {
    return this.request('PUT', `/lists/${listId}/closed`, { value: 'true' });
  }

  // Card operations
  async getCardsByList(listId: string) {
    return this.request('GET', `/lists/${listId}/cards`);
  }

  async addCardToList(listId: string, name: string, description?: string, dueDate?: string, labels?: string[]) {
    const params: Record<string, any> = { idList: listId, name };
    if (description) params.desc = description;
    if (dueDate) params.due = dueDate;
    if (labels && labels.length > 0) params.idLabels = labels.join(',');
    return this.request('POST', '/cards', params);
  }

  async archiveCard(cardId: string) {
    return this.request('PUT', `/cards/${cardId}/closed`, { value: 'true' });
  }

  async attachImageToCard(cardId: string, imageUrl: string, name?: string) {
    const params: Record<string, any> = { url: imageUrl };
    if (name) params.name = name;
    return this.request('POST', `/cards/${cardId}/attachments`, params);
  }

  async moveCard(cardId: string, listId: string, pos?: string) {
    const result = await this.request('PUT', `/cards/${cardId}/idList`, { value: listId });
    if (pos) {
      await this.request('PUT', `/cards/${cardId}/pos`, { value: pos });
    }
    return result;
  }

  async updateCardDetails(cardId: string, name?: string, description?: string, dueDate?: string, labels?: string[]) {
    const params: Record<string, any> = {};
    if (name !== undefined) params.name = name;
    if (description !== undefined) params.desc = description;
    if (dueDate !== undefined) params.due = dueDate;
    if (labels !== undefined) params.idLabels = labels.join(',');
    return this.request('PUT', `/cards/${cardId}`, params);
  }

  async getMyCards() {
    return this.request('GET', '/members/me/cards', { fields: 'id,name,idList,idBoard,url' });
  }

  async getRecentActivity(boardId: string, limit = 10) {
    return this.request('GET', `/boards/${boardId}/actions`, { limit });
  }

  async listWorkspaces() {
    return this.request('GET', '/members/me/organizations');
  }
}

// Lazy client initialization
let _client: TrelloClient | null = null;

function getClient(): TrelloClient {
  if (!_client) {
    const apiKey = process.env.TRELLO_API_KEY;
    const token = process.env.TRELLO_TOKEN;
    const debug = ['1', 'true', 'yes'].includes(process.env.MCP_DEBUG?.toLowerCase() || '0');
    _client = new TrelloClient(apiKey, token, TRELLO_BASE_URL, debug);
  }
  return _client;
}

// === TOOLS ===

// Server info tool
server.addTool({
  name: 'get_server_info',
  description: 'Get information about the MCP server, environment, and active Trello context',
  parameters: z.object({}),
  execute: async () => {
    console.log('tool:get_server_info');
    // Return as plain text string for server info
    return `Server: ${SERVER_NAME} v2.0.0
Environment: ${process.env.ENVIRONMENT || 'development'}
Node: ${process.version}
Active Board: ${activeBoard || 'none'}
Active Workspace: ${activeWorkspace || 'none'}
Uptime: ${process.uptime()}s`;
  },
});

// Board management tools
server.addTool({
  name: 'get_active_board_info',
  description: 'Get information about the currently active board',
  parameters: z.object({}),
  execute: async () => {
    console.log('tool:get_active_board_info');
    if (!activeBoard) {
      throw new TrelloError('No active board set. Provide TRELLO_BOARD_ID or call set_active_board.');
    }
    const client = getClient();
    const result = await client.getBoard(activeBoard);
    // Return formatted text response
    return `Board: ${result.name}\nID: ${result.id}\nURL: ${result.url}`;
  },
});

server.addTool({
  name: 'set_active_board',
  description: 'Set the active board for future operations',
  parameters: z.object({
    boardId: z.string().describe('ID of the board to set as active'),
  }),
  execute: async ({ boardId }) => {
    console.log(`tool:set_active_board boardId=${boardId}`);
    activeBoard = boardId;
    return `Active board set to: ${boardId}`;
  },
});

server.addTool({
  name: 'list_boards',
  description: 'List all boards the user has access to',
  parameters: z.object({}),
  execute: async () => {
    console.log('tool:list_boards');
    const client = getClient();
    const boards = await client.listBoards();
    // Format boards as readable text
    if (!boards || boards.length === 0) {
      return 'No boards found';
    }
    return boards.map((b: any) => `• ${b.name} (ID: ${b.id})`).join('\n');
  },
});

server.addTool({
  name: 'list_boards_in_workspace',
  description: 'List all boards in a specific workspace',
  parameters: z.object({
    workspaceId: z.string().describe('ID of the workspace to list boards from'),
  }),
  execute: async ({ workspaceId }) => {
    console.log(`tool:list_boards_in_workspace workspaceId=${workspaceId}`);
    const client = getClient();
    const boards = await client.listBoardsInWorkspace(workspaceId);
    if (!boards || boards.length === 0) {
      return 'No boards found in this workspace';
    }
    return boards.map((b: any) => `• ${b.name} (ID: ${b.id})`).join('\n');
  },
});

// Workspace tools
server.addTool({
  name: 'list_workspaces',
  description: 'List all workspaces the user has access to',
  parameters: z.object({}),
  execute: async () => {
    console.log('tool:list_workspaces');
    const client = getClient();
    const workspaces = await client.listWorkspaces();
    if (!workspaces || workspaces.length === 0) {
      return 'No workspaces found';
    }
    return workspaces.map((w: any) => `• ${w.displayName || w.name} (ID: ${w.id})`).join('\n');
  },
});

server.addTool({
  name: 'set_active_workspace',
  description: 'Set the active workspace for future operations',
  parameters: z.object({
    workspaceId: z.string().describe('ID of the workspace to set as active'),
  }),
  execute: async ({ workspaceId }) => {
    console.log(`tool:set_active_workspace workspaceId=${workspaceId}`);
    activeWorkspace = workspaceId;
    return `Active workspace set to: ${workspaceId}`;
  },
});

// List management tools
server.addTool({
  name: 'get_lists',
  description: 'Retrieve all lists from the specified board',
  parameters: z.object({
    boardId: z.string().optional().describe('Board ID (uses active board if not provided)'),
  }),
  execute: async ({ boardId }) => {
    const board = boardId || activeBoard;
    console.log(`tool:get_lists boardId=${board}`);
    if (!board) {
      throw new TrelloError('No board specified and no active board is set.');
    }
    const client = getClient();
    const lists = await client.getLists(board);
    // Format lists as readable text
    if (!lists || lists.length === 0) {
      return 'No lists found on this board';
    }
    return lists
      .filter((l: any) => !l.closed)
      .map((l: any) => `• ${l.name} (ID: ${l.id})`)
      .join('\n');
  },
});

server.addTool({
  name: 'add_list_to_board',
  description: 'Add a new list to the board',
  parameters: z.object({
    name: z.string().describe('Name of the new list'),
    boardId: z.string().optional().describe('Board ID (uses active board if not provided)'),
  }),
  execute: async ({ name, boardId }) => {
    const board = boardId || activeBoard;
    console.log(`tool:add_list_to_board name=${name} boardId=${board}`);
    if (!board) {
      throw new TrelloError('No board specified and no active board is set.');
    }
    const client = getClient();
    const list = await client.addListToBoard(board, name);
    return `List created successfully!\nName: ${list.name}\nID: ${list.id}`;
  },
});

server.addTool({
  name: 'archive_list',
  description: 'Send a list to the archive',
  parameters: z.object({
    listId: z.string().describe('ID of the list to archive'),
  }),
  execute: async ({ listId }) => {
    console.log(`tool:archive_list listId=${listId}`);
    const client = getClient();
    await client.archiveList(listId);
    return `List ${listId} has been archived successfully`;
  },
});

// Card management tools
server.addTool({
  name: 'get_cards_by_list_id',
  description: 'Fetch cards from a specific Trello list',
  parameters: z.object({
    listId: z.string().describe('ID of the Trello list'),
  }),
  execute: async ({ listId }) => {
    console.log(`tool:get_cards_by_list_id listId=${listId}`);
    const client = getClient();
    const cards = await client.getCardsByList(listId);
    if (!cards || cards.length === 0) {
      return 'No cards found in this list';
    }
    return cards.map((c: any) => `• ${c.name}${c.due ? ` (Due: ${c.due})` : ''} - ID: ${c.id}`).join('\n');
  },
});

server.addTool({
  name: 'add_card_to_list',
  description: 'Add a new card to a specified list',
  parameters: z.object({
    listId: z.string().describe('ID of the list to add the card to'),
    name: z.string().describe('Name of the card'),
    description: z.string().optional().describe('Description of the card'),
    dueDate: z.string().optional().describe('Due date for the card (ISO 8601 format)'),
    labels: z.array(z.string()).optional().describe('Array of label IDs to apply to the card'),
  }),
  execute: async ({ listId, name, description, dueDate, labels }) => {
    console.log(`tool:add_card_to_list listId=${listId} name=${name}`);
    const client = getClient();
    const card = await client.addCardToList(listId, name, description, dueDate, labels);
    return `Card created successfully!\nName: ${card.name}\nID: ${card.id}${card.url ? `\nURL: ${card.url}` : ''}`;
  },
});

server.addTool({
  name: 'archive_card',
  description: 'Send a card to the archive',
  parameters: z.object({
    cardId: z.string().describe('ID of the card to archive'),
  }),
  execute: async ({ cardId }) => {
    console.log(`tool:archive_card cardId=${cardId}`);
    const client = getClient();
    await client.archiveCard(cardId);
    return `Card ${cardId} has been archived successfully`;
  },
});

server.addTool({
  name: 'attach_image_to_card',
  description: 'Attach an image to a card directly from a URL',
  parameters: z.object({
    cardId: z.string().describe('ID of the card to attach the image to'),
    imageUrl: z.string().describe('URL of the image to attach'),
    name: z.string().optional().describe('Optional name for the attachment (defaults to "Image Attachment")'),
  }),
  execute: async ({ cardId, imageUrl, name }) => {
    console.log(`tool:attach_image_to_card cardId=${cardId} imageUrl=${imageUrl}`);
    const client = getClient();
    const attachment = await client.attachImageToCard(cardId, imageUrl, name || 'Image Attachment');
    return `Image attached successfully to card ${cardId}\nAttachment ID: ${attachment.id}`;
  },
});

server.addTool({
  name: 'move_card',
  description: 'Move a card to a different list',
  parameters: z.object({
    cardId: z.string().describe('ID of the card to move'),
    listId: z.string().describe('ID of the target list'),
    position: z.string().optional().describe('Position in the list (top, bottom, or a number)'),
  }),
  execute: async ({ cardId, listId, position }) => {
    console.log(`tool:move_card cardId=${cardId} listId=${listId} position=${position}`);
    const client = getClient();
    await client.moveCard(cardId, listId, position);
    return `Card ${cardId} moved to list ${listId}${position ? ` at position ${position}` : ''}`;
  },
});

server.addTool({
  name: 'update_card_details',
  description: "Update an existing card's details",
  parameters: z.object({
    cardId: z.string().describe('ID of the card to update'),
    name: z.string().optional().describe('New name for the card'),
    description: z.string().optional().describe('New description for the card'),
    dueDate: z.string().optional().describe('New due date for the card (ISO 8601 format)'),
    labels: z.array(z.string()).optional().describe('New array of label IDs for the card'),
  }),
  execute: async ({ cardId, name, description, dueDate, labels }) => {
    console.log(`tool:update_card_details cardId=${cardId}`);
    const client = getClient();
    const card = await client.updateCardDetails(cardId, name, description, dueDate, labels);
    return `Card ${cardId} updated successfully${name ? `\nName: ${name}` : ''}${dueDate ? `\nDue: ${dueDate}` : ''}`;
  },
});

server.addTool({
  name: 'get_my_cards',
  description: 'Fetch all cards assigned to the current user',
  parameters: z.object({}),
  execute: async () => {
    console.log('tool:get_my_cards');
    const client = getClient();
    const cards = await client.getMyCards();
    if (!cards || cards.length === 0) {
      return 'No cards assigned to you';
    }
    return cards.map((c: any) => `• ${c.name} (Board: ${c.idBoard}) - ID: ${c.id}`).join('\n');
  },
});

server.addTool({
  name: 'get_recent_activity',
  description: 'Fetch recent activity on the Trello board',
  parameters: z.object({
    boardId: z.string().optional().describe('Board ID (uses active board if not provided)'),
    limit: z.number().optional().default(10).describe('Number of activities to fetch (default: 10)'),
  }),
  execute: async ({ boardId, limit }) => {
    const board = boardId || activeBoard;
    console.log(`tool:get_recent_activity boardId=${board} limit=${limit}`);
    if (!board) {
      throw new TrelloError('No board specified and no active board is set.');
    }
    const client = getClient();
    const activities = await client.getRecentActivity(board, limit);
    if (!activities || activities.length === 0) {
      return 'No recent activity found';
    }
    return activities.map((a: any) => `• ${a.type}: ${a.data?.card?.name || a.data?.list?.name || 'Unknown'} by ${a.memberCreator?.fullName || 'Unknown'}`).join('\n');
  },
});


// === SERVER STARTUP ===
async function main() {
  const port = process.env.PORT || 3000;
  const host = process.env.HOST || '0.0.0.0';
  
  console.log(`Starting ${SERVER_NAME} v2.0.0 (TypeScript)`);
  console.log(`Environment: ${process.env.ENVIRONMENT || 'development'}`);
  console.log(`Debug mode: ${DEBUG ? 'enabled' : 'disabled'}`);
  console.log(`Credentials configured: ${!!(API_KEY && TOKEN) ? 'yes' : 'no'}`);
  
  if (activeBoard) {
    console.log(`Active board: ${activeBoard}`);
  }
  if (activeWorkspace) {
    console.log(`Active workspace: ${activeWorkspace}`);
  }

  // Start FastMCP server with HTTP streaming
  await server.start({
    transportType: 'httpStream',
    httpStream: {
      port: Number(port),
      host,
      endpoint: '/mcp', // MCP endpoint
    },
  });
  
  console.log(`Server running at http://${host}:${port}`);
  console.log(`MCP endpoint: http://${host}:${port}/mcp`);
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
  console.log('\nShutting down gracefully...');
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\nShutting down gracefully...');
  process.exit(0);
});

// Start the server
main().catch((error) => {
  console.error('Failed to start server:', error);
  process.exit(1);
});