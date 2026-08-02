/** Task Timeline — real Agent Runtime events via SSE */
import { useEffect, useState, useRef } from 'react'
import { useAppStore } from '../../stores/appStore'
import { Bot, Wrench, Brain, CheckCircle2, XCircle, Clock, Search, FileText, Terminal, MessageSquare, GitBranch, Radio, Zap } from 'lucide-react'

interface LiveEvent {
  type: string
  source: string
  data: Record<string, any>
  args?: Record<string, any>
  timestamp: number
}

interface TimelineStep {
  id: number
  type: string
  source: string
  label: string
  detail: string
  status: 'running' | 'done' | 'error'
  time: string
}

const TOOL_LABELS: Record<string, string> = {
  read_file: '读取文件', write_file: '写入文件', list_files: '列出文件',
  shell: '执行命令', search_memory: '搜索记忆', save_to_memory: '保存记忆',
  create_project_workspace: '创建项目', save_checkpoint: '保存进度',
}

export default function TaskTimeline() {
  const { sessionId, messages, isLoading } = useAppStore()
  const [liveSteps, setLiveSteps] = useState<TimelineStep[]>([])
  const [connected, setConnected] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const stepCounter = useRef(0)
  const esRef = useRef<EventSource | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Connect SSE when sessionId changes
  useEffect(() => {
    if (!sessionId) return
    const streamUrl = `/api/events/stream?session_id=${sessionId}`

    const es = new EventSource(streamUrl)
    esRef.current = es
    setLiveSteps([])
    stepCounter.current = 0

    es.onopen = () => setConnected(true)
    es.onerror = () => setConnected(false)

    es.onmessage = (e) => {
      try {
        const evt: LiveEvent = JSON.parse(e.data)
        stepCounter.current += 1
        const step = buildStep(stepCounter.current, evt)
        setLiveSteps(prev => [...prev.slice(-80), step])
      } catch {}
    }

    return () => {
      es.close()
      esRef.current = null
      setConnected(false)
    }
  }, [sessionId])

  // Timer during loading
  useEffect(() => {
    if (isLoading) {
      setElapsed(0)
      timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000)
    } else {
      if (timerRef.current) clearInterval(timerRef.current)
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [isLoading])

  // Merge historical steps from messages when no live session
  const historySteps: TimelineStep[] = []
  let histId = 0
  for (const msg of messages) {
    if (msg.role === 'user') {
      historySteps.push({
        id: ++histId, type: 'user:message', source: 'user',
        label: '用户请求', detail: (msg as any).content?.slice(0, 120) || '',
        status: 'done', time: new Date(msg.timestamp).toLocaleTimeString(),
      })
    }
    const tc = (msg as any).toolCalls
    if (tc && Array.isArray(tc)) {
      for (const t of tc) {
        historySteps.push({
          id: ++histId, type: 'tool:call:end', source: (msg as any).agent || 'agent',
          label: t.tool, detail: t.output?.slice(0, 100) || '',
          status: t.success ? 'done' : 'error',
          time: new Date(msg.timestamp).toLocaleTimeString(),
        })
      }
    }
    if (msg.role === 'assistant' && (msg as any).content?.length > 0) {
      historySteps.push({
        id: ++histId, type: 'agent:completed', source: (msg as any).agent || 'ceo',
        label: '任务完成', detail: `${(msg as any).iterations || '?'} iterations · ${((msg as any).toolCalls || []).length} tools`,
        status: 'done', time: new Date(msg.timestamp).toLocaleTimeString(),
      })
    }
  }

  const displaySteps = liveSteps.length > 0 ? liveSteps : historySteps

  if (displaySteps.length === 0 && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-600 space-y-3">
        <GitBranch size={32} className="text-gray-700" />
        <p className="text-sm">任务时间线</p>
        <p className="text-xs text-gray-700">发送消息后，Agent 执行过程实时显示在这里</p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-400 flex items-center gap-2">
          <Radio size={14} className={connected ? 'text-green-400' : 'text-gray-600'} />
          任务时间线
        </h3>
        <div className="flex items-center gap-3 text-[10px] text-gray-600">
          {isLoading && (
            <span className="text-kernel-400 animate-pulse flex items-center gap-1">
              <Zap size={10} /> {elapsed}s
            </span>
          )}
          <span className={connected ? 'text-green-500' : 'text-gray-700'}>
            {connected ? '● 实时' : '○ 离线'}
          </span>
          <span>{displaySteps.length} 步</span>
        </div>
      </div>

      {/* Step list */}
      <div className="space-y-0">
        {displaySteps.map((step, i) => {
          const isLast = i === displaySteps.length - 1
          const isRunning = step.status === 'running'
          const Icon = pickIcon(step)

          return (
            <div key={step.id} className="relative">
              {!isLast && (
                <div className="absolute left-[15px] top-[28px] w-[2px] h-[calc(100%-8px)] bg-gray-800" />
              )}

              <div className="flex gap-3 py-1.5">
                {/* Icon */}
                <div className={`w-[32px] h-[32px] rounded-lg flex items-center justify-center flex-shrink-0 z-10 ${
                  isRunning ? 'bg-blue-900/50 border border-blue-700' :
                  step.status === 'error' ? 'bg-red-900/50 border border-red-800' :
                  step.type === 'agent:completed' ? 'bg-green-900/30 border border-green-800' :
                  step.type === 'user:message' ? 'bg-gray-700 border border-gray-600' :
                  'bg-gray-800 border border-gray-700'
                }`}>
                  <Icon size={14} className={
                    isRunning ? 'text-blue-400 animate-spin' :
                    step.status === 'error' ? 'text-red-400' :
                    step.type === 'agent:completed' ? 'text-green-400' :
                    step.type === 'user:message' ? 'text-gray-300' :
                    'text-kernel-400'
                  } />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-xs font-medium ${
                      isRunning ? 'text-blue-400' :
                      step.status === 'error' ? 'text-red-400' :
                      'text-gray-300'
                    }`}>
                      {step.label}
                    </span>
                    {step.status === 'done' && <CheckCircle2 size={10} className="text-green-500 flex-shrink-0" />}
                    {step.status === 'error' && <XCircle size={10} className="text-red-500 flex-shrink-0" />}
                    {isRunning && <span className="text-[10px] text-blue-400/60">运行中</span>}
                  </div>
                  {step.detail && (
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-2 break-all">{step.detail}</p>
                  )}
                  <div className="flex items-center gap-2 mt-0.5 text-[10px] text-gray-700">
                    <span className="flex items-center gap-1"><Bot size={10} />{step.source}</span>
                    <span>{step.time}</span>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function buildStep(id: number, evt: LiveEvent): TimelineStep {
  const t = evt.type
  const time = new Date(evt.timestamp * 1000).toLocaleTimeString()

  if (t === 'agent:started') {
    return { id, type: t, source: evt.source, label: `${evt.source} 启动`, detail: (evt.data.goal || '').slice(0, 120), status: 'done', time }
  }
  if (t === 'agent:thinking') {
    return { id, type: t, source: evt.source, label: `${evt.source} 思考中`, detail: `iteration ${evt.data.iteration}`, status: 'running', time }
  }
  if (t === 'tool:call:start') {
    const tool = evt.data.tool || ''
    return { id, type: t, source: evt.source, label: TOOL_LABELS[tool] || tool, detail: evt.args ? JSON.stringify(evt.args).slice(0, 120) : '', status: 'running', time }
  }
  if (t === 'tool:call:end') {
    const tool = evt.data.tool || ''
    const ok = evt.data.success !== false
    return { id, type: t, source: evt.source, label: (TOOL_LABELS[tool] || tool) + (ok ? ' ✓' : ' ✗'), detail: '', status: ok ? 'done' : 'error', time }
  }
  if (t === 'agent:completed') {
    return { id, type: t, source: evt.source, label: `${evt.source} 完成`, detail: `${evt.data.output_length || 0} chars`, status: 'done', time }
  }
  if (t === 'agent:error') {
    return { id, type: t, source: evt.source, label: `${evt.source} 错误`, detail: evt.data.error || '', status: 'error', time }
  }
  return { id, type: t, source: evt.source, label: t, detail: '', status: 'running', time }
}

function pickIcon(step: TimelineStep): typeof Wrench {
  if (step.label.includes('启动')) return Zap
  if (step.label.includes('思考')) return Brain
  if (step.label.includes('搜索') || step.label.includes('读取') || step.label.includes('列出')) return Search
  if (step.label.includes('写入') || step.label.includes('创建')) return FileText
  if (step.label.includes('执行') || step.label.includes('命令')) return Terminal
  if (step.label.includes('保存')) return Brain
  if (step.label.includes('完成')) return CheckCircle2
  if (step.label.includes('错误')) return XCircle
  if (step.type === 'user:message') return MessageSquare
  return Wrench
}
