/**
 * MCP Connection Error Handler
 * Fixes #115: Fail fast and surface error when MCP tools are unavailable
 */

export class MCPConnectionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "MCPConnectionError";
  }
}

export interface MCPConnectionResult {
  connected: boolean;
  error?: string;
}

/**
 * Check MCP server connection and fail fast if unavailable
 */
export async function checkMCPConnection(): Promise<MCPConnectionResult> {
  try {
    // Attempt to connect to MCP server
    const response = await fetch("http://localhost:3000/mcp/health", {
      method: "GET",
      timeout: 5000,
    });
    
    if (!response.ok) {
      throw new MCPConnectionError("MCP server returned error status");
    }
    
    return { connected: true };
  } catch (error) {
    // Fail fast - don't silently fall back to LLM
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    
    return {
      connected: false,
      error: `MCP tools unavailable: ${errorMessage}. Please check your MCP server connection.`,
    };
  }
}

/**
 * Wrapper for engine operations that require MCP
 */
export async function withMCPCheck<T>(
  operation: () => Promise<T>
): Promise<T> {
  const connection = await checkMCPConnection();
  
  if (!connection.connected) {
    // Surface error to UI instead of falling back to LLM
    throw new MCPConnectionError(connection.error || "MCP tools unavailable");
  }
  
  return operation();
}

