import { useEffect, useState } from 'react'
import { Brain, Search, BookOpen, Lightbulb, History } from 'lucide-react'
import { getProfile, searchMemory } from '../../lib/api'

interface MemoryEntry {
  id: string;
  title: string;
  content: string;
  category: string;
  tags: string[];
  importance: number;
}

export default function MemoryViewer() {
  const [profile, setProfile] = useState<any>(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<MemoryEntry[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getProfile().then(setProfile).catch(() => {})
  }, [])

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    try {
      const res = await searchMemory(query)
      setResults(res.results || [])
    } catch {
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <h2 className="text-lg font-semibold flex items-center gap-2 mb-6">
        <Brain size={20} className="text-kernel-400" />
        记忆系统
      </h2>

      {/* Profile card */}
      {profile && (
        <div className="card mb-6">
          <h3 className="text-sm font-medium text-gray-400 mb-3">👤 用户档案</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">名称</span>
              <span>{profile.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">技能水平</span>
              <span>{profile.skill_level}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">技术栈</span>
              <span className="text-kernel-400">{(profile.tech_stack || []).join(', ')}</span>
            </div>
            <div>
              <span className="text-gray-500 block mb-1">目标</span>
              <div className="flex flex-wrap gap-1">
                {(profile.goals || []).map((g: string, i: number) => (
                  <span key={i} className="text-xs bg-kernel-900/50 text-kernel-400 px-2 py-0.5 rounded-full">
                    {g}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="搜索记忆..."
          className="flex-1 input-field text-sm"
        />
        <button onClick={handleSearch} disabled={loading} className="btn-primary text-sm">
          <Search size={14} />
        </button>
      </div>

      {/* Search results */}
      {results.length > 0 && (
        <div className="space-y-2">
          {results.map((entry) => (
            <div key={entry.id} className="card hover:border-gray-700 transition-colors">
              <div className="flex items-start gap-2">
                {entry.category === 'knowledge' && <BookOpen size={14} className="text-blue-400 mt-0.5" />}
                {entry.category === 'decision' && <Lightbulb size={14} className="text-yellow-400 mt-0.5" />}
                {entry.category === 'experience' && <History size={14} className="text-green-400 mt-0.5" />}
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium">{entry.title}</h4>
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{entry.content}</p>
                  {entry.tags && entry.tags.length > 0 && (
                    <div className="flex gap-1 mt-2">
                      {entry.tags.map((tag: string) => (
                        <span key={tag} className="text-xs bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 rounded-full border-2 border-kernel-500 flex items-center justify-center text-xs text-kernel-400">
                    {Math.round(entry.importance * 100)}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {results.length === 0 && query && !loading && (
        <p className="text-sm text-gray-500 text-center py-8">没有找到匹配的记忆</p>
      )}
    </div>
  )
}
