import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Wrench, User, Bot } from 'lucide-react'
import { useAppStore, nextId } from '../stores/appStore'
import { sendMessage } from '../lib/api'

export default function ChatPanel() {
  const {
    sessionId, setSessionId,
    messages, addMessage,
    isLoading, setLoading,
    currentAgent,
  } = useAppStore()

  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

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
      }
      addMessage(assistantMsg)
    } catch (err: any) {
      addMessage({
        id: nextId(),
        role: 'system' as const,
        content: `❌ 错误: ${err.message}`,
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
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 space-y-2">
            <Bot size={48} className="text-gray-700" />
            <p className="text-lg font-medium">Personal AI OS v0.1</p>
            <p className="text-sm">你的 AI 员工已就位，输入目标开始工作</p>
            <div className="flex flex-wrap gap-2 mt-4">
              {['帮我分析一个创业想法', '创建一个新项目', '搜索我的知识库'].map((hint) => (
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
          <div className="flex items-center gap-2 text-gray-400 px-4">
            <Loader2 size={16} className="animate-spin" />
            <span className="text-sm">AI 思考中...</span>
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

function MessageBubble({ msg }: { msg: { id: string; role: string; content: string; toolCalls?: any[] } }) {
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
