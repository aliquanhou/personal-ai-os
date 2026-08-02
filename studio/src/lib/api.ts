/** API client for Personal AI OS */

const BASE = '/api';

export interface ChatResponse {
  session_id: string;
  agent: string;
  response: string;
  tool_calls: Array<{ tool: string; args: Record<string, unknown>; success: boolean; output: string }>;
  iterations: number;
}

export interface Agent {
  id: string;
  name: string;
  description: string;
}

export async function sendMessage(message: string, agent: string = 'project_manager', sessionId?: string): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, agent, session_id: sessionId || '' }),
  });
  if (!res.ok) throw new Error(`Chat error: ${res.status}`);
  return res.json();
}

export async function listAgents(): Promise<Agent[]> {
  const res = await fetch(`${BASE}/agents`);
  if (!res.ok) throw new Error(`Agents error: ${res.status}`);
  const data = await res.json();
  return data.agents;
}

export async function getProfile() {
  const res = await fetch(`${BASE}/memory/profile`);
  return res.json();
}

export async function searchMemory(query: string) {
  const res = await fetch(`${BASE}/memory/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  return res.json();
}

export async function getConversations(sessionId: string) {
  const res = await fetch(`${BASE}/memory/conversations/${sessionId}`);
  return res.json();
}

export async function getProjects(status: string = 'active') {
  const res = await fetch(`${BASE}/projects?status=${status}`);
  return res.json();
}
