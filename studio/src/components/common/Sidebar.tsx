import { useEffect, useState } from 'react'
import { Bot, MessageSquare, FolderOpen, Brain, PanelLeftClose, PanelLeft, GitBranch, Package } from 'lucide-react'
import { useAppStore } from '../../stores/appStore'
import { listAgents, Agent } from '../../lib/api'
import ChatPanel from '../chat/ChatPanel'
import WorkspacePanel from '../workspace/WorkspacePanel'
import MemoryViewer from '../memory_viewer/MemoryViewer'
import TaskTimeline from '../timeline/TaskTimeline'
import PluginPanel from '../plugins/PluginPanel'

export default function Sidebar() {
  const { currentAgent, setCurrentAgent, sidebarOpen, toggleSidebar, activeTab, setActiveTab } = useAppStore()
  const [agents, setAgents] = useState<Agent[]>([])

  useEffect(() => {
    listAgents().then(setAgents).catch(() => {})
  }, [])

  return (
    <>
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-0'} bg-gray-900 border-r border-gray-800 flex flex-col transition-all duration-200 overflow-hidden`}>
        {/* Logo */}
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-lg font-bold tracking-tight">
            <span className="text-kernel-400">AI</span> OS
          </h1>
          <p className="text-xs text-gray-600 mt-0.5">v0.1 — Personal AI Employee</p>
        </div>

        {/* Navigation */}
        <nav className="p-3 space-y-1">
          {[
            { id: 'chat' as const, icon: MessageSquare, label: '对话' },
            { id: 'workspace' as const, icon: FolderOpen, label: '工作区' },
            { id: 'memory' as const, icon: Brain, label: '记忆' },
            { id: 'timeline' as const, icon: GitBranch, label: 'Timeline' },
            { id: 'plugins' as const, icon: Package, label: 'Plugins' },
            { id: 'agents' as const, icon: Bot, label: 'Agents' },
          ].map(({ id, icon: Icon, label }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                activeTab === id
                  ? 'bg-kernel-600/20 text-kernel-400'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </nav>

        {/* Agent selector */}
        <div className="p-3 border-t border-gray-800 mt-auto">
          <p className="text-xs text-gray-600 mb-2 px-1">当前 Agent</p>
          <select
            value={currentAgent}
            onChange={(e) => setCurrentAgent(e.target.value)}
            className="w-full input-field text-sm"
          >
            {agents.map((a) => (
              <option key={a.id} value={a.name}>{a.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <div className="h-12 border-b border-gray-800 flex items-center px-4 gap-3 flex-shrink-0">
          <button onClick={toggleSidebar} className="text-gray-500 hover:text-gray-300">
            {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeft size={18} />}
          </button>
          <span className="text-sm text-gray-400">
            {activeTab === 'chat' && '💬 对话'}
            {activeTab === 'workspace' && '📁 工作区'}
            {activeTab === 'memory' && '🧠 记忆系统'}
            {activeTab === 'timeline' && '⏱️ 任务时间线'}
            {activeTab === 'plugins' && '📦 插件管理'}
            {activeTab === 'agents' && '🤖 智能体'}
          </span>
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'chat' && <ChatPanel />}
          {activeTab === 'workspace' && <WorkspacePanel />}
          {activeTab === 'memory' && <MemoryViewer />}
          {activeTab === 'timeline' && <TaskTimeline />}
          {activeTab === 'plugins' && <PluginPanel />}
          {activeTab === 'agents' && <AgentsPanel />}
        </div>
      </div>
    </>
  )
}

function AgentsPanel() {
  const [agents, setAgents] = useState<Agent[]>([])

  useEffect(() => {
    listAgents().then(setAgents).catch(() => {})
  }, [])

  return (
    <div className="h-full overflow-y-auto p-6">
      <h2 className="text-lg font-semibold flex items-center gap-2 mb-6">
        <Bot size={20} className="text-kernel-400" />
        可用 Agents
      </h2>
      <div className="grid gap-3">
        {agents.map((a) => (
          <div key={a.id} className="card hover:border-gray-700 transition-colors">
            <h3 className="font-medium text-kernel-400">{a.name}</h3>
            <p className="text-sm text-gray-500 mt-1">{a.description}</p>
            <span className="text-xs text-gray-700 mt-2 block">ID: {a.id}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
