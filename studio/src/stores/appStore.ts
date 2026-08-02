/** Zustand store for Personal AI OS Studio v1.1 */

import { create } from 'zustand';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  toolCalls?: Array<{ tool: string; args: Record<string, unknown>; success: boolean; output: string }>;
  timestamp: number;
  agent?: string;
  iterations?: number;
}

interface AppState {
  // Chat
  sessionId: string;
  messages: Message[];
  isLoading: boolean;
  currentAgent: string;

  // Sessions
  savedSessions: Array<{ id: string; label: string; timestamp: number }>;

  // UI
  sidebarOpen: boolean;
  activeTab: 'chat' | 'workspace' | 'memory' | 'timeline' | 'plugins' | 'agents';

  // Actions
  setSessionId: (id: string) => void;
  addMessage: (msg: Message) => void;
  setMessages: (msgs: Message[]) => void;
  setLoading: (loading: boolean) => void;
  setCurrentAgent: (agent: string) => void;
  toggleSidebar: () => void;
  setActiveTab: (tab: 'chat' | 'workspace' | 'memory' | 'timeline' | 'plugins' | 'agents') => void;
  // Session persistence
  saveCurrentSession: () => void;
  loadSession: (id: string) => void;
  newSession: () => void;
  loadSavedSessions: () => void;
}

let msgCounter = 0;
const nextId = () => `msg-${++msgCounter}-${Date.now()}`;

const SESSION_KEY = 'paios_sessions';

function loadSessionsFromStorage(): Array<{ id: string; label: string; timestamp: number }> {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY) || '[]');
  } catch { return []; }
}

function saveSessionsToStorage(sessions: Array<{ id: string; label: string; timestamp: number }>) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(sessions.slice(-50)));
}

function loadCurrentId(): string {
  return localStorage.getItem('paios_current_session') || '';
}

function saveCurrentId(id: string) {
  localStorage.setItem('paios_current_session', id);
}

export const useAppStore = create<AppState>((set, get) => ({
  sessionId: loadCurrentId(),
  messages: [],
  isLoading: false,
  currentAgent: 'ceo',
  savedSessions: loadSessionsFromStorage(),
  sidebarOpen: true,
  activeTab: 'chat',

  setSessionId: (id) => {
    saveCurrentId(id);
    set({ sessionId: id });
  },

  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),

  setMessages: (msgs) => set({ messages: msgs }),

  setLoading: (loading) => set({ isLoading: loading }),

  setCurrentAgent: (agent) => set({ currentAgent: agent }),

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  setActiveTab: (tab) => set({ activeTab: tab }),

  // ── Session Persistence ──

  saveCurrentSession: () => {
    const { sessionId, messages } = get();
    if (!sessionId || messages.length === 0) return;
    const label = messages.find(m => m.role === 'user')?.content?.slice(0, 60) || '对话';
    const timestamp = Date.now();
    const sessions = loadSessionsFromStorage().filter(s => s.id !== sessionId);
    sessions.unshift({ id: sessionId, label, timestamp });
    saveSessionsToStorage(sessions);
    saveCurrentId(sessionId);
    set({ savedSessions: sessions });
  },

  loadSession: (id: string) => {
    saveCurrentId(id);
    set({ sessionId: id, messages: [], activeTab: 'chat' });
    // Fetch messages from backend
    return fetch(`/api/memory/conversations/${id}`)
      .then(res => res.json())
      .then(data => {
        const raw = (data.messages || []).map((m: any) => {
          let meta = m.metadata;
          if (typeof meta === 'string') {
            try { meta = JSON.parse(meta); } catch { meta = {}; }
          }
          return {
            id: m.id || nextId(),
            role: m.role as Message['role'],
            content: m.content || '',
            toolCalls: meta?.tool_calls || undefined,
            agent: meta?.agent || undefined,
            iterations: meta?.iterations || undefined,
            timestamp: m.created_at ? new Date(m.created_at).getTime() : Date.now(),
          };
        });
        // Dedup: skip consecutive identical messages
        const msgs: any[] = [];
        for (const m of raw) {
          const prev = msgs[msgs.length - 1];
          if (prev && prev.role === m.role && prev.content === m.content) continue;
          msgs.push(m);
        }
        if (msgs.length > 0) {
          msgCounter = msgs.length + 1;
          set({ messages: msgs });
        }
      })
      .catch(() => {}); // Backend not available
  },

  newSession: () => {
    const newId = '';
    saveCurrentId('');
    set({ sessionId: '', messages: [] });
  },

  loadSavedSessions: () => {
    set({ savedSessions: loadSessionsFromStorage() });
  },
}));

export { nextId };
