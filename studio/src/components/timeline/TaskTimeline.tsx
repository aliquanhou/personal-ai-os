/** Task Timeline — visual execution pipeline (Sprint 7.4)

Shows the agent workflow as a vertical timeline:
  User Request → Agent Plan → Skill Selected → Tool Exec → Validation → Result
*/

import { useState, useEffect } from 'react'
import { useAppStore } from '../../stores/appStore'
import {
  MessageSquare, Brain, Wrench, CheckCircle2, XCircle,
  Clock, Bot, ArrowDown, Play, GitBranch,
} from 'lucide-react'

interface TimelineStep {
  id: string
  phase: 'request' | 'plan' | 'skill' | 'tool' | 'validate' | 'result'
  label: string
  detail: string
  agent: string
  status: 'pending' | 'running' | 'done' | 'error'
  timestamp: number
}

const PHASE_ICONS: Record<string, typeof MessageSquare> = {
  request: MessageSquare,
  plan: GitBranch,
  skill: Brain,
  tool: Wrench,
  validate: CheckCircle2,
  result: CheckCircle2,
}

const PHASE_LABELS: Record<string, string> = {
  request: 'Request',
  plan: 'Plan',
  skill: 'Skill',
  tool: 'Execute',
  validate: 'Verify',
  result: 'Result',
}

export default function TaskTimeline() {
  const { messages, isLoading } = useAppStore()
  const [steps, setSteps] = useState<TimelineStep[]>([])

  useEffect(() => {
    if (messages.length === 0) {
      setSteps([])
      return
    }

    const newSteps: TimelineStep[] = []

    // User request
    const userMsgs = messages.filter(m => m.role === 'user')
    if (userMsgs.length > 0) {
      newSteps.push({
        id: 'req-' + userMsgs.length,
        phase: 'request',
        label: 'User Request',
        detail: userMsgs[userMsgs.length - 1].content.slice(0, 80),
        agent: 'user',
        status: 'done',
        timestamp: userMsgs[userMsgs.length - 1].timestamp,
      })
    }

    // Agent phases from tool calls
    const assistantMsgs = messages.filter(m => m.role === 'assistant')
    for (const msg of assistantMsgs.slice(-1)) {
      // Agent plan inferred from first response
      if (msg.content && msg.content.length > 0) {
        // Detect plan from markdown headings
        const planMatch = msg.content.match(/###\s*[📋🎯]?\s*(理解|任务拆解|项目计划|分析)/)
        if (planMatch) {
          newSteps.push({
            id: 'plan-' + msg.id,
            phase: 'plan',
            label: 'Agent Plan',
            detail: msg.content.slice(msg.content.indexOf(planMatch[0]), msg.content.indexOf(planMatch[0]) + 100),
            agent: 'ceo',
            status: 'done',
            timestamp: msg.timestamp,
          })
        }
      }

      // Tool executions
      if (msg.toolCalls) {
        for (const tc of msg.toolCalls) {
          newSteps.push({
            id: 'tool-' + msg.id + '-' + tc.tool,
            phase: 'tool',
            label: tc.tool,
            detail: tc.output?.slice(0, 100) || tc.tool,
            agent: 'agent',
            status: tc.success ? 'done' : 'error',
            timestamp: msg.timestamp,
          })
        }
      }

      // Result
      if (msg.content && msg.content.length > 50) {
        const hasResult = msg.content.match(/###\s*[✅📝]?\s*(执行结果|完成|报告|简报)/)
        if (hasResult) {
          newSteps.push({
            id: 'result-' + msg.id,
            phase: 'result',
            label: 'Result',
            detail: 'Task completed',
            agent: 'ceo',
            status: 'done',
            timestamp: msg.timestamp,
          })
        }
      }
    }

    // Currently running
    if (isLoading) {
      newSteps.push({
        id: 'running',
        phase: 'tool',
        label: 'Executing...',
        detail: 'Agent is working on your request',
        agent: 'agent',
        status: 'running',
        timestamp: Date.now(),
      })
    }

    setSteps(newSteps)
  }, [messages, isLoading])

  if (steps.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-600 space-y-3">
        <GitBranch size={32} className="text-gray-700" />
        <p className="text-sm">No task history yet</p>
        <p className="text-xs text-gray-700">Send a message to see the execution timeline</p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-4">
      <h3 className="text-sm font-medium text-gray-400 mb-4 flex items-center gap-2">
        <Clock size={14} />
        Task Timeline
      </h3>

      <div className="space-y-0">
        {steps.map((step, i) => {
          const Icon = PHASE_ICONS[step.phase] || Bot
          const isLast = i === steps.length - 1
          const isRunning = step.status === 'running'

          return (
            <div key={step.id} className="relative">
              {/* Connector line */}
              {!isLast && (
                <div className="absolute left-[15px] top-[28px] w-[2px] h-[calc(100%-8px)] bg-gray-800" />
              )}

              <div className="flex gap-3 py-2">
                {/* Icon */}
                <div className={`w-[32px] h-[32px] rounded-lg flex items-center justify-center flex-shrink-0 z-10 ${
                  step.status === 'running' ? 'bg-blue-900/50 border border-blue-700 animate-pulse' :
                  step.status === 'error' ? 'bg-red-900/50 border border-red-800' :
                  step.status === 'done' ? 'bg-gray-800 border border-gray-700' :
                  'bg-gray-900 border border-gray-800'
                }`}>
                  <Icon size={14} className={
                    isRunning ? 'text-blue-400' :
                    step.status === 'error' ? 'text-red-400' :
                    'text-gray-500'
                  } />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-300">
                      {PHASE_LABELS[step.phase] || step.phase}
                    </span>
                    {step.status === 'done' && <CheckCircle2 size={12} className="text-green-500" />}
                    {step.status === 'error' && <XCircle size={12} className="text-red-500" />}
                    {isRunning && <Play size={12} className="text-blue-400 animate-pulse" />}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5 truncate">
                    {step.detail}
                  </p>
                  {step.agent !== 'user' && (
                    <span className="text-[10px] text-gray-700 mt-0.5">
                      {step.agent}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {steps.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-800">
          <div className="flex items-center justify-between text-[10px] text-gray-600">
            <span>{steps.length} steps</span>
            <span>
              {steps.filter(s => s.status === 'error').length > 0
                ? `${steps.filter(s => s.status === 'error').length} errors`
                : steps.every(s => s.status === 'done' || s.status === 'running')
                  ? 'Active'
                  : 'Pending'}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
