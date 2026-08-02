/** Zustand store for Personal AI OS Studio */

import { create } from 'zustand';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  toolCalls?: Array<{ tool: string; args: Record<string, unknown>; success: boolean; output: string }>;
  timestamp: number;
}

interface AppState {
  // Chat
  sessionId: string;
  messages: Message[];
  isLoading: boolean;
  currentAgent: string;

  // UI
  sidebarOpen: boolean;
  activeTab: 'chat' | 'workspace' | 'memory' | 'timeline' | 'agents';

  // Actions
  setSessionId: (id: string) => void;
  addMessage: (msg: Message) => void;
  setLoading: (loading: boolean) => void;
  setCurrentAgent: (agent: string) => void;
  toggleSidebar: () => void;
  setActiveTab: (tab: 'chat' | 'workspace' | 'memory' | 'timeline' | 'agents') => void;
}

let msgCounter = 0;
const nextId = () => `msg-${++msgCounter}-${Date.now()}`;

export const useAppStore = create<AppState>((set) => ({
  sessionId: '',
  messages: [],
  isLoading: false,
  currentAgent: 'project_manager',
  sidebarOpen: true,
  activeTab: 'chat',

  setSessionId: (id) => set({ sessionId: id }),
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  setLoading: (loading) => set({ isLoading: loading }),
  setCurrentAgent: (agent) => set({ currentAgent: agent }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setActiveTab: (tab) => set({ activeTab: tab }),
}));

export { nextId };
