/** ChatPanel v1.6 — streaming text + inline tool cards */
import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Wrench, User, Bot, History, Plus, CheckCircle2, XCircle } from 'lucide-react'
import { useAppStore, nextId } from '../../stores/appStore'

const TOOL_LABELS: Record<string, string> = {
  read_file: '读取文件', write_file: '写入文件', list_files: '列出文件',
  shell: '执行命令', search_memory: '搜索记忆', save_to_memory: '保存记忆',
  create_project_workspace: '创建项目', save_checkpoint: '保存进度',
}

export default function ChatPanel() {
  const {
    sessionId, setSessionId,
    messages, addMessage, setMessages,
    isLoading, setLoading,
    currentAgent,
    loadSession, saveCurrentSession, newSession,
    savedSessions,
  } = useAppStore()

  const [input, setInput] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const [streamText, setStreamText] = useState('')
  const [streamTools, setStreamTools] = useState<any[]>([])
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const elapsedRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, streamText])
  useEffect(() => { inputRef.current?.focus() }, [])

  useEffect(() => {
    if (historyLoaded) return
    const stored = localStorage.getItem('paios_current_session')
    if (stored) { loadSession(stored); setHistoryLoaded(true) }
    else setHistoryLoaded(true)
  }, [loadSession, historyLoaded])

  useEffect(() => {
    if (isLoading) {
      setElapsed(0)
      elapsedRef.current = setInterval(() => setElapsed(e => e + 1), 1000)
    } else {
      if (elapsedRef.current) clearInterval(elapsedRef.current)
      setElapsed(0)
    }
    return () => { if (elapsedRef.current) clearInterval(elapsedRef.current) }
  }, [isLoading])

  const handleStreamResponse = async (body: string, sid: string) => {
    setStreamText('')
    setStreamTools([])
    let fullResponse = ''
    const toolLog: any[] = []

    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      })

      if (!res.ok) throw new Error(`Server error: ${res.status}`)

      const reader = res.body?.getReader()
      if (!reader) throw new Error('No response stream')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const evt = JSON.parse(line.slice(6))

            if (evt.type === 'session') {
              if (!sid) setSessionId(evt.session_id)
            } else if (evt.type === 'text') {
              fullResponse += evt.content
              setStreamText(fullResponse)
            } else if (evt.type === 'tool_start') {
              setStreamTools(prev => [...prev, { tool: evt.tool, args: evt.args, status: 'running' }])
            } else if (evt.type === 'tool_end') {
              setStreamTools(prev => prev.map(t =>
                t.tool === evt.tool && t.status === 'running'
                  ? { ...t, status: evt.success ? 'done' : 'error', output: evt.output }
                  : t
              ))
              toolLog.push({ tool: evt.tool, success: evt.success, output: evt.output || '', args: {} })
            } else if (evt.type === 'done') {
              fullResponse = evt.response || fullResponse
              setStreamText(fullResponse)
              setStreamTools([])
            } else if (evt.type === 'error') {
              throw new Error(evt.message)
            }
          } catch { /* skip parse errors */ }
        }
      }
    } catch (err: any) {
      setStreamTools([])
      addMessage({
        id: nextId(), role: 'system' as const,
        content: `❌ ${err.message || 'Stream error'}`,
        timestamp: Date.now(),
      })
      return
    }

    // Add complete response
    addMessage({
      id: nextId(), role: 'assistant' as const,
      content: fullResponse, toolCalls: toolLog,
      timestamp: Date.now(), agent: currentAgent,
      iterations: 0,
    })
    setStreamText('')
    setStreamTools([])
    saveCurrentSession()
  }

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isLoading) return

    const userMsg = { id: nextId(), role: 'user' as const, content: text, timestamp: Date.now() }
    addMessage(userMsg)
    setInput('')
    setLoading(true)

    const body = JSON.stringify({ message: text, agent: currentAgent, session_id: sessionId })
    await handleStreamResponse(body, sessionId)
    setLoading(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Session bar */}
      {savedSessions.length > 0 && (
        <div className="flex-shrink-0 border-b border-gray-800 px-4 py-2 flex items-center gap-2 overflow-x-auto">
          <History size={12} className="text-gray-600 flex-shrink-0" />
          {savedSessions.slice(0, 8).map(s => (
            <button key={s.id} onClick={() => loadSession(s.id)}
              className={`text-[11px] px-2 py-1 rounded whitespace-nowrap ${sessionId === s.id ? 'bg-kernel-600/20 text-kernel-400' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'}`}
            >{s.label.slice(0, 20)}</button>
          ))}
          <button onClick={newSession} className="text-[11px] px-2 py-1 rounded text-gray-500 hover:text-gray-300 hover:bg-gray-800 ml-auto flex items-center gap-1"><Plus size={12} />新</button>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 space-y-2">
            <Bot size={48} className="text-gray-700" />
            <p className="text-lg font-medium">Personal AI OS v1.0</p>
            <p className="text-sm">你的 AI 团队已就位，输入目标开始工作</p>
            <div className="flex flex-wrap gap-2 mt-4">
              {['帮我分析一个创业想法', '帮我创建一个博客网站', '分析AI Agent市场趋势'].map(hint => (
                <button key={hint} onClick={() => setInput(hint)}
                  className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-400 px-3 py-1.5 rounded-full transition-colors"
                >{hint}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}

        {/* Streaming output: text + inline tool cards */}
        {(isLoading) && (
          <div className="space-y-3">
            {/* Loading indicator */}
            <div className="flex items-center gap-3 px-4 py-2 bg-gray-800/40 rounded-xl border border-gray-700/50">
              <Loader2 size={16} className="animate-spin text-kernel-400" />
              <span className="text-sm text-gray-300">{currentAgent} 工作中 · {elapsed}s</span>
            </div>

            {/* Inline tool cards */}
            {streamTools.map((t, i) => (
              <div key={i} className="flex items-center gap-2 px-3 py-1.5 bg-gray-800/50 rounded-lg border border-gray-700/30 text-xs">
                <Wrench size={12} className="text-kernel-400" />
                <span className="text-gray-400">{TOOL_LABELS[t.tool] || t.tool}</span>
                {t.status === 'running' && <Loader2 size={10} className="animate-spin text-blue-400" />}
                {t.status === 'done' && <CheckCircle2 size={10} className="text-green-500" />}
                {t.status === 'error' && <XCircle size={10} className="text-red-500" />}
              </div>
            ))}

            {/* Streaming text */}
            {streamText && (
              <div className="bg-gray-800 rounded-xl px-4 py-2.5">
                <div className="text-sm text-gray-100 whitespace-pre-wrap leading-relaxed">
                  {streamText}
                  <span className="inline-block w-2 h-4 bg-kernel-400 animate-pulse ml-0.5 align-middle" />
                </div>
              </div>
            )}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 p-4">
        <div className="flex gap-2">
          <input ref={inputRef} type="text" value={input}
            onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown}
            placeholder="输入你的目标或问题..." className="flex-1 input-field" disabled={isLoading} />
          <button onClick={handleSend} disabled={isLoading || !input.trim()}
            className="btn-primary flex items-center gap-2">
            {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}发送
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
        {!isUser && !isSystem && msg.agent && (
          <div className="flex items-center gap-2 mb-1 text-[10px] text-gray-500">
            <span className="text-kernel-400">{msg.agent}</span>
            {msg.iterations != null && <span>{msg.iterations} iterations</span>}
          </div>
        )}
        <div className={`rounded-xl px-4 py-2.5 ${
          isUser ? 'bg-kernel-600 text-white' :
          isSystem ? 'bg-red-900/50 text-red-300 border border-red-800' :
          'bg-gray-800 text-gray-100'
        }`}>
          <div className="message-content text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</div>
        </div>
        {msg.toolCalls && msg.toolCalls.length > 0 && (
          <div className="mt-2 space-y-1">
            {msg.toolCalls.map((tc: any, i: number) => (
              <div key={i} className="flex items-center gap-2 text-xs text-gray-500 bg-gray-900 rounded-lg px-3 py-1.5">
                <Wrench size={12} />
                <span className="text-kernel-400">{TOOL_LABELS[tc.tool] || tc.tool}</span>
                <span>{tc.success ? '✅' : '❌'}</span>
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
