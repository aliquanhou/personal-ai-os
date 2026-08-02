/** Task Timeline — shows real agent execution steps from tool calls */
import { useEffect, useState } from 'react'
import { useAppStore } from '../../stores/appStore'
import { Bot, Wrench, Brain, CheckCircle2, XCircle, Clock, Search, FileText, Terminal, MessageSquare, GitBranch } from 'lucide-react'

const TOOL_ICONS: Record<string, typeof Wrench> = {}
const getToolIcon = (tool: string) => {
  if (tool.includes('search') || tool.includes('memory')) return Search
  if (tool.includes('write') || tool.includes('file')) return FileText
  if (tool.includes('read') || tool.includes('list')) return Search
  if (tool.includes('shell')) return Terminal
  return Wrench
}

export default function TaskTimeline() {
  const { messages, isLoading } = useAppStore()
  const [steps, setSteps] = useState<any[]>([])
  const [elapsed, setElapsed] = useState(0)

  // Elapsed timer during loading
  useEffect(() => {
    if (!isLoading) return
    setElapsed(0)
    const t = setInterval(() => setElapsed(e => e + 1), 1000)
    return () => clearInterval(t)
  }, [isLoading])

  useEffect(() => {
    const built: any[] = []
    let stepId = 0

    for (const msg of messages) {
      // User request
      if (msg.role === 'user') {
        built.push({
          id: ++stepId,
          type: 'request',
          icon: MessageSquare,
          label: '用户请求',
          detail: (msg as any).content?.slice(0, 120) || '',
          status: 'done',
        })
      }

      // Tool calls from assistant
      const tc = (msg as any).toolCalls
      if (tc && Array.isArray(tc)) {
        for (const t of tc) {
          const Icon = getToolIcon(t.tool)
          built.push({
            id: ++stepId,
            type: 'tool',
            icon: Icon,
            label: t.tool,
            detail: (t.output || '').slice(0, 120),
            status: t.success ? 'done' : 'error',
            agent: (msg as any).agent || 'agent',
          })
        }
      }

      // Agent response summary
      if (msg.role === 'assistant' && (msg as any).content?.length > 0) {
        const hasPlan = (msg as any).content?.includes('📋') || (msg as any).content?.includes('🎯')
        const hasResult = (msg as any).content?.includes('✅') || (msg as any).content?.includes('完成')
        built.push({
          id: ++stepId,
          type: hasResult ? 'result' : 'plan',
          icon: hasResult ? CheckCircle2 : Brain,
          label: hasResult ? '任务完成' : 'Agent 分析',
          detail: hasResult
            ? `${(msg as any).agent || 'ceo'} · ${(msg as any).iterations || '?'} iterations · ${((msg as any).toolCalls || []).length} tools`
            : '分析目标并制定执行计划',
          status: 'done',
          agent: (msg as any).agent || 'ceo',
        })
      }
    }

    // Live step during loading
    if (isLoading) {
      built.push({
        id: ++stepId,
        type: 'running',
        icon: GitBranch,
        label: '执行中...',
        detail: `Agent 正在处理你的请求 · ${elapsed}s`,
        status: 'running',
      })
    }

    setSteps(built)
  }, [messages, isLoading, elapsed])

  if (steps.length === 0 && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-600 space-y-3">
        <GitBranch size={32} className="text-gray-700" />
        <p className="text-sm">暂无任务记录</p>
        <p className="text-xs text-gray-700">发送消息后，执行过程会在这里显示</p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-4">
      <h3 className="text-sm font-medium text-gray-400 mb-4 flex items-center gap-2">
        <Clock size={14} />
        任务时间线
        {isLoading && (
          <span className="text-xs text-kernel-400 animate-pulse ml-auto">{elapsed}s</span>
        )}
      </h3>

      <div className="space-y-0">
        {steps.map((step, i) => {
          const Icon = step.icon || Bot
          const isLast = i === steps.length - 1
          const isRunning = step.status === 'running'

          return (
            <div key={step.id} className="relative">
              {!isLast && (
                <div className="absolute left-[15px] top-[28px] w-[2px] h-[calc(100%-8px)] bg-gray-800" />
              )}

              <div className="flex gap-3 py-2">
                {/* Icon */}
                <div className={`w-[32px] h-[32px] rounded-lg flex items-center justify-center flex-shrink-0 z-10 ${
                  isRunning ? 'bg-blue-900/50 border border-blue-700' :
                  step.status === 'error' ? 'bg-red-900/50 border border-red-800' :
                  step.type === 'result' ? 'bg-green-900/30 border border-green-800' :
                  step.type === 'request' ? 'bg-gray-700 border border-gray-600' :
                  'bg-gray-800 border border-gray-700'
                }`}>
                  <Icon size={14} className={
                    isRunning ? 'text-blue-400 animate-pulse' :
                    step.status === 'error' ? 'text-red-400' :
                    step.type === 'result' ? 'text-green-400' :
                    step.type === 'request' ? 'text-gray-300' :
                    'text-kernel-400'
                  } />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-medium ${
                      isRunning ? 'text-blue-400' :
                      step.status === 'error' ? 'text-red-400' :
                      step.type === 'result' ? 'text-green-400' :
                      'text-gray-300'
                    }`}>
                      {step.label}
                    </span>
                    {step.status === 'done' && step.type !== 'running' && (
                      <CheckCircle2 size={12} className="text-green-500 flex-shrink-0" />
                    )}
                    {step.status === 'error' && (
                      <XCircle size={12} className="text-red-500 flex-shrink-0" />
                    )}
                    {isRunning && (
                      <span className="text-[10px] text-blue-400/60 animate-pulse">· {elapsed}s</span>
                    )}
                  </div>
                  {step.detail && (
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-2 break-all">
                      {step.detail}
                    </p>
                  )}
                  {step.agent && (
                    <span className="text-[10px] text-gray-700 mt-0.5 inline-flex items-center gap-1">
                      <Bot size={10} /> {step.agent}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {steps.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-800 flex items-center justify-between text-[10px] text-gray-600">
          <span>{steps.length} 个步骤</span>
          <span>
            {steps.filter(s => s.status === 'error').length > 0
              ? `${steps.filter(s => s.status === 'error').length} 个错误`
              : steps.every(s => s.status === 'done' || s.status === 'running')
                ? '活跃'
                : ''}
          </span>
        </div>
      )}
    </div>
  )
}
