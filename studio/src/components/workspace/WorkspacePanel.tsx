import { useEffect, useState } from 'react'
import { FolderOpen, File, ChevronRight, Folder, RefreshCw } from 'lucide-react'
import { useAppStore } from '../../stores/appStore'

interface FileEntry {
  name: string
  isDir: boolean
  path: string
  size: number
}

export default function WorkspacePanel() {
  const [files, setFiles] = useState<FileEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [currentPath, setCurrentPath] = useState('workspace/projects')
  const [error, setError] = useState('')

  const fetchFiles = async (path: string) => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/workspace?status=`)
      const data = await res.json()
      const projects = (data.projects || []).map((p: any) => ({
        name: p.name || p.slug,
        isDir: true,
        path: `workspace/projects/${p.slug}`,
        size: 0,
      }))
      setFiles(projects)
    } catch {
      setError('Cannot connect to workspace')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchFiles(currentPath) }, [])

  const formatSize = (bytes: number) => {
    if (bytes === 0) return ''
    if (bytes < 1024) return `${bytes}B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 flex-shrink-0">
        <div className="flex items-center gap-2">
          <FolderOpen size={16} className="text-kernel-400" />
          <h3 className="text-sm font-medium text-gray-300">Workspace</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-600">{currentPath}</span>
          <button
            onClick={() => fetchFiles(currentPath)}
            className="text-gray-600 hover:text-gray-400 transition-colors"
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* File listing */}
      <div className="flex-1 overflow-y-auto">
        {error && (
          <div className="text-xs text-red-400 px-4 py-2">{error}</div>
        )}

        {loading ? (
          <div className="text-xs text-gray-600 text-center py-8">Loading...</div>
        ) : files.length === 0 ? (
          <div className="text-center py-8 text-gray-600">
            <Folder size={32} className="mx-auto mb-2 text-gray-700" />
            <p className="text-sm">No projects yet</p>
            <p className="text-xs mt-1">Create one by chatting with the CEO Agent</p>
          </div>
        ) : (
          <div className="py-1">
            {files.map((f, i) => (
              <div
                key={i}
                className="flex items-center gap-2 px-4 py-1.5 hover:bg-gray-800/50 cursor-pointer transition-colors text-xs"
              >
                {f.isDir ? (
                  <Folder size={14} className="text-kernel-400 flex-shrink-0" />
                ) : (
                  <File size={14} className="text-gray-500 flex-shrink-0" />
                )}
                <span className="text-gray-300 truncate flex-1">{f.name}</span>
                {f.size > 0 && (
                  <span className="text-gray-700 flex-shrink-0">{formatSize(f.size)}</span>
                )}
                {f.isDir && (
                  <ChevronRight size={12} className="text-gray-700 flex-shrink-0" />
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-800 px-4 py-2 flex items-center justify-between text-[10px] text-gray-700 flex-shrink-0">
        <span>{files.length} items</span>
        <span>{files.filter(f => f.isDir).length} projects</span>
      </div>
    </div>
  )
}
