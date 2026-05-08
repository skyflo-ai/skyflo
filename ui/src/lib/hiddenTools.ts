/** Tools that run silently (no approval UI, no tool execution cards). */
export const HIDDEN_SYSTEM_TOOLS = new Set(["memory_remember"]);

export function isHiddenSystemTool(toolName?: string): boolean {
  return !!toolName && HIDDEN_SYSTEM_TOOLS.has(toolName);
}
