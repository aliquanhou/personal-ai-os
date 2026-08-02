/** API client for Personal AI OS v1.1.2 */

const BASE = '/api';
const TIMEOUT_MS = 300000; // 5 minute timeout for complex agent tasks

export interface ChatResponse {
  session_id: string;
  agent: string;
  response: string;
  tool_calls: Array<{ tool: string; args: Record<string, unknown>; success: boolean; output: string }>;
  iterations: number;
  checkpoint_count?: number;
}

export interface Agent {
  id: string;
  name: string;
  description: string;
}

async function fetchWithTimeout(url: string, options: RequestInit, timeout = TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    return response;
  } finally {
    clearTimeout(timer);
  }
}

export async function sendMessage(message: string, agent: string = 'ceo', sessionId?: string): Promise<ChatResponse> {
  const res = await fetchWithTimeout(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, agent, session_id: sessionId || '' }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '无法读取错误详情');
    throw new Error(`服务器错误 ${res.status}: ${text.slice(0, 200)}`);
  }
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
