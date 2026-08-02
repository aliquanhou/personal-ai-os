import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Wrench, User, Bot, Brain, GitBranch, History, Plus } from 'lucide-react'
import { useAppStore, nextId } from '../../stores/appStore'
import { sendMessage } from '../../lib/api'

const STATUS_PHASES = [
  'CEO 分析目标...',
  '制定执行计划...',
  'Agent 工作中...',
  '整理结果...',
]

export default function ChatPanel() {
  const {
    sessionId, setSessionId,
    messages, addMessage,
    isLoading, setLoading,
    currentAgent,
    loadSession, saveCurrentSession, newSession,
    savedSessions, loadSavedSessions,
  } = useAppStore()

  const [input, setInput] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const [statusIdx, setStatusIdx] = useState(0)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const elapsedRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Restore session on mount
  useEffect(() => {
    if (historyLoaded) return
    const stored = localStorage.getItem('paios_current_session')
    if (stored) {
      loadSession(stored)
      setHistoryLoaded(true)
    } else {
      setHistoryLoaded(true)
    }
  }, [loadSession, historyLoaded])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Elapsed timer + rotating status during loading
  useEffect(() => {
    if (isLoading) {
      setElapsed(0)
      setStatusIdx(0)
      elapsedRef.current = setInterval(() => {
        setElapsed(e => e + 1)
        setStatusIdx(s => (s + 1) % STATUS_PHASES.length)
      }, 5000)
    } else {
      if (elapsedRef.current) clearInterval(elapsedRef.current)
      elapsedRef.current = null
      setElapsed(0)
      setStatusIdx(0)
    }
    return () => {
      if (elapsedRef.current) clearInterval(elapsedRef.current)
    }
  }, [isLoading])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isLoading) return

    const userMsg = { id: nextId(), role: 'user' as const, content: text, timestamp: Date.now() }
    addMessage(userMsg)
    setInput('')
    setLoading(true)

    try {
      const result = await sendMessage(text, currentAgent, sessionId)
      if (!sessionId) setSessionId(result.session_id)

      const assistantMsg = {
        id: nextId(),
        role: 'assistant' as const,
        content: result.response,
        toolCalls: result.tool_calls,
        timestamp: Date.now(),
        agent: result.agent,
        iterations: result.iterations,
      }
      addMessage(assistantMsg)
      saveCurrentSession()
    } catch (err: any) {
      const errMsg = err.message || String(err)
      let diagnostic = ''

      if (err.name === 'AbortError' || errMsg.includes('abort') || errMsg.includes('signal')) {
        diagnostic = `⏱️ 任务超时（超过 5 分钟）

最后状态：
• Agent: ${currentAgent}
• 已运行: ${elapsed} 秒
• 当前阶段: ${STATUS_PHASES[statusIdx]}

可能原因：
1. 任务太复杂，Agent 执行时间超过限制
2. LLM API 响应慢
3. Agent 在等待某个阻塞操作

建议：
• 将大任务拆分为多个小任务
• 用 python main.py chat 在 CLI 执行（无超时限制）
• 检查 DeepSeek API 是否正常`
      } else if (errMsg.includes('NetworkError') || errMsg.includes('fetch')) {
        diagnostic = `🔌 网络连接失败

• 后端服务可能未启动
• 检查: curl http://127.0.0.1:8001/health`
      } else {
        diagnostic = `❌ 任务执行失败

错误: ${errMsg}

可能原因：
1. 后端 Agent Runtime 异常
2. LLM API 调用失败
3. 工具执行出错

建议：
• 查看后端日志: python main.py serve 的终端输出
• 用简单任务测试: "说OK"`
      }

      addMessage({
        id: nextId(),
        role: 'system' as const,
        content: diagnostic,
        timestamp: Date.now(),
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Session bar */}
      {savedSessions.length > 0 && (
        <div className="flex-shrink-0 border-b border-gray-800 px-4 py-2 flex items-center gap-2 overflow-x-auto">
          <History size={12} className="text-gray-600 flex-shrink-0" />
          {savedSessions.slice(0, 8).map(s => (
            <button
              key={s.id}
              onClick={() => loadSession(s.id)}
              className={`text-[11px] px-2 py-1 rounded whitespace-nowrap transition-colors ${
                sessionId === s.id
                  ? 'bg-kernel-600/20 text-kernel-400'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
              }`}
              title={s.label}
            >
              {s.label.slice(0, 20)}
            </button>
          ))}
          <button
            onClick={newSession}
            className="text-[11px] px-2 py-1 rounded text-gray-500 hover:text-gray-300 hover:bg-gray-800 flex items-center gap-1 flex-shrink-0 ml-auto"
            title="新对话"
          >
            <Plus size={12} /> 新
          </button>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 space-y-2">
            <Bot size={48} className="text-gray-700" />
            <p className="text-lg font-medium">Personal AI OS v1.0</p>
            <p className="text-sm">你的 AI 团队已就位，输入目标开始工作</p>
            <div className="flex flex-wrap gap-2 mt-4">
              {['帮我分析一个创业想法', '帮我创建一个个人博客网站', '分析AI Agent市场趋势'].map((hint) => (
                <button
                  key={hint}
                  onClick={() => setInput(hint)}
                  className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-400 px-3 py-1.5 rounded-full transition-colors"
                >
                  {hint}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}

        {isLoading && (
          <div className="px-4 py-3">
            <div className="bg-gray-800/50 rounded-xl px-4 py-3 border border-gray-700/50">
              {/* Agent status header */}
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-lg bg-kernel-600/30 flex items-center justify-center">
                  <Loader2 size={16} className="animate-spin text-kernel-400" />
                </div>
                <div>
                  <p className="text-sm text-gray-200 font-medium">
                    {STATUS_PHASES[statusIdx]}
                  </p>
                  <p className="text-xs text-gray-500">
                    Agent: {currentAgent} · 已运行 {elapsed}s
                  </p>
                </div>
              </div>
              {/* Progress bar */}
              <div className="w-full bg-gray-700 rounded-full h-1 mt-2 overflow-hidden">
                <div className="bg-kernel-500 h-1 rounded-full animate-pulse"
                  style={{ width: `${Math.min(90, elapsed * 3)}%`, transition: 'width 0.5s' }} />
              </div>
              {/* Phase hints */}
              <div className="flex gap-4 mt-2 text-[10px] text-gray-600">
                <span className="flex items-center gap-1">
                  <Brain size={10} /> 分析
                </span>
                <span className="flex items-center gap-1">
                  <GitBranch size={10} /> 计划
                </span>
                <span className="flex items-center gap-1">
                  <Wrench size={10} /> 执行
                </span>
                <span className="flex items-center gap-1">
                  <Bot size={10} /> 输出
                </span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-800 p-4">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你的目标或问题..."
            className="flex-1 input-field"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="btn-primary flex items-center gap-2"
          >
            {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            发送
          </button>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ msg }: { msg: { id: string; role: string; content: string; toolCalls?: any[]; agent?: string; iterations?: number } }) {
  const isUser = msg.role === 'user'
  const isSystem = msg.role === 'system'

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && (
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${isSystem ? 'bg-red-900' : 'bg-kernel-700'}`}>
          {isSystem ? <Wrench size={14} /> : <Bot size={14} />}
        </div>
      )}
      <div className={`max-w-[80%] ${isUser ? 'order-first' : ''}`}>
        {/* Agent + timing badge */}
        {!isUser && !isSystem && msg.agent && (
          <div className="flex items-center gap-2 mb-1 text-[10px] text-gray-500">
            <span className="text-kernel-400">{msg.agent}</span>
            {msg.iterations != null && (
              <span>{msg.iterations} iterations</span>
            )}
          </div>
        )}
        <div className={`rounded-xl px-4 py-2.5 ${
          isUser
            ? 'bg-kernel-600 text-white'
            : isSystem
            ? 'bg-red-900/50 text-red-300 border border-red-800'
            : 'bg-gray-800 text-gray-100'
        }`}>
          <div className="message-content text-sm leading-relaxed whitespace-pre-wrap">
            {msg.content}
          </div>
        </div>

        {msg.toolCalls && msg.toolCalls.length > 0 && (
          <div className="mt-2 space-y-1">
            {msg.toolCalls.map((tc: any, i: number) => (
              <div key={i} className="flex items-center gap-2 text-xs text-gray-500 bg-gray-900 rounded-lg px-3 py-1.5">
                <Wrench size={12} />
                <span className="text-kernel-400">{tc.tool}</span>
                <span>{tc.success ? '✅' : '❌'}</span>
                <span className="truncate">{tc.output?.slice(0, 80)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-gray-700 flex items-center justify-center flex-shrink-0">
          <User size={14} />
        </div>
      )}
    </div>
  )
}
