import axios from "axios";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/$/, "");

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

export interface MCPServerOverview {
  capabilities: Record<string, unknown>;
  stats: {
    tools: number;
    prompts: number;
    resources: number;
    tool_invocations: number;
    last_invoked_at?: string | null;
    last_error?: string | null;
  };
  tools: string[];
  connected: boolean;
}

export interface MCPConfig {
  mcpServers: Record<string, unknown>;
}

export async function fetchServers(): Promise<Record<string, MCPServerOverview>> {
  const response = await apiClient.get<{ servers: Record<string, MCPServerOverview> }>("/servers");
  return response.data.servers;
}

export async function fetchStats(): Promise<Record<string, MCPServerOverview>> {
  const response = await apiClient.get<{ stats: Record<string, MCPServerOverview> }>("/stats");
  return response.data.stats;
}

export async function fetchConfig(): Promise<MCPConfig> {
  const response = await apiClient.get<{ config: MCPConfig }>("/config");
  return response.data.config;
}

export async function updateConfig(config: MCPConfig): Promise<void> {
  await apiClient.put("/config", config);
}

export async function addServers(patch: MCPConfig["mcpServers"]): Promise<void> {
  await apiClient.post("/servers", { mcpServers: patch });
}

export async function removeServer(name: string): Promise<void> {
  await apiClient.delete(`/servers/${encodeURIComponent(name)}`);
}
