import { useEffect, useState } from 'react'
import { FolderOpen, Plus, CheckCircle2, Circle } from 'lucide-react'
import { getProjects } from '../../lib/api'

interface Project {
  id: string;
  name: string;
  description: string;
  status: string;
}

export default function WorkspacePanel() {
  const [projects, setProjects] = useState<Project[]>([])

  useEffect(() => {
    getProjects().then((res) => setProjects(res.projects || [])).catch(() => {})
  }, [])

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <FolderOpen size={20} className="text-kernel-400" />
          工作区
        </h2>
        <button className="btn-secondary text-sm flex items-center gap-1">
          <Plus size={14} />
          新建项目
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="text-center text-gray-500 py-12">
          <FolderOpen size={48} className="mx-auto mb-4 text-gray-700" />
          <p>还没有项目</p>
          <p className="text-sm mt-1">在聊天中告诉 AI 你想做什么，它会自动创建项目</p>
        </div>
      ) : (
        <div className="space-y-3">
          {projects.map((p) => (
            <div key={p.id} className="card hover:border-gray-700 cursor-pointer transition-colors">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-medium">{p.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">{p.description}</p>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  p.status === 'active' ? 'bg-green-900/50 text-green-400' : 'bg-gray-800 text-gray-500'
                }`}>
                  {p.status}
                </span>
              </div>
              <div className="mt-3 flex items-center gap-4 text-xs text-gray-600">
                <span className="flex items-center gap-1"><CheckCircle2 size={12} /> 0 任务</span>
                <span className="flex items-center gap-1"><Circle size={12} /> 0 进行中</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
