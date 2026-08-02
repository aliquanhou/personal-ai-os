import { useEffect, useState } from 'react'
import { Package, CheckCircle2, XCircle, Bot, Shield, Star, Zap } from 'lucide-react'

interface PluginInfo {
  name: string; version: string; display_name: string; description: string
  author: string; category: string; skills: string[]
  target_agents: string[]; enabled: boolean; official?: boolean
}

const API = '/api/plugins'

const CAT_COLORS: Record<string, string> = {
  development: 'text-blue-400', research: 'text-green-400',
  writing: 'text-yellow-400', knowledge: 'text-purple-400',
  network: 'text-cyan-400',
}

export default function PluginPanel() {
  const [plugins, setPlugins] = useState<PluginInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchPlugins = async () => {
    setLoading(true)
    try {
      const res = await fetch(API)
      const data = await res.json()
      setPlugins(data.plugins || [])
      setError('')
    } catch {
      setError('Failed to load plugins')
    } finally { setLoading(false) }
  }

  useEffect(() => { fetchPlugins() }, [])

  const togglePlugin = async (name: string, enabled: boolean) => {
    const endpoint = enabled ? `${API}/${name}/uninstall` : `${API}/${name}/install`
    try { await fetch(endpoint, { method: 'POST' }); await fetchPlugins() }
    catch { setError(`Failed to ${enabled ? 'disable' : 'enable'} ${name}`) }
  }

  const official = plugins.filter(p => (p as any).official)
  const community = plugins.filter(p => !(p as any).official)
  const active = plugins.filter(p => p.enabled)

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <Package size={16} className="text-kernel-400" />
          Plugin Marketplace
        </h3>
        <span className="text-xs text-gray-600">{active.length}/{plugins.length} active</span>
      </div>

      {error && (
        <div className="text-xs text-red-400 bg-red-900/30 px-3 py-2 rounded mb-3">{error}</div>
      )}

      {loading ? (
        <div className="text-xs text-gray-600 text-center py-8">Loading...</div>
      ) : (
        <>
          {/* Official Plugins */}
          {official.length > 0 && (
            <>
              <div className="flex items-center gap-2 mb-2">
                <Shield size={12} className="text-kernel-400" />
                <span className="text-[11px] text-gray-500 font-medium">OFFICIAL</span>
              </div>
              <div className="space-y-2 mb-4">
                {official.map(p => (
                  <PluginCard key={p.name} p={p} onToggle={togglePlugin} />
                ))}
              </div>
            </>
          )}

          {/* Community Plugins */}
          {community.length > 0 && (
            <>
              <div className="flex items-center gap-2 mb-2 mt-4">
                <Zap size={12} className="text-gray-600" />
                <span className="text-[11px] text-gray-600 font-medium">COMMUNITY</span>
              </div>
              <div className="space-y-2">
                {community.map(p => (
                  <PluginCard key={p.name} p={p} onToggle={togglePlugin} />
                ))}
              </div>
            </>
          )}
        </>
      )}

      {plugins.length === 0 && !loading && (
        <div className="text-center py-8 text-gray-600">
          <Package size={32} className="mx-auto mb-2 text-gray-700" />
          <p className="text-sm">No plugins installed</p>
          <p className="text-xs mt-1">Place plugin.json files in the plugins/ directory</p>
        </div>
      )}

      <div className="mt-6 pt-4 border-t border-gray-800">
        <p className="text-[10px] text-gray-700">
          Official plugins are maintained by the Personal AI OS team.
          Community plugins can be added to <code className="text-gray-600">plugins/</code>.
        </p>
      </div>
    </div>
  )
}

function PluginCard({ p, onToggle }: { p: PluginInfo & { official?: boolean }, onToggle: (n: string, e: boolean) => void }) {
  return (
    <div className={`card hover:border-gray-700 transition-colors relative ${p.enabled ? 'border-gray-800' : 'border-gray-800/50 opacity-60'}`}>
      {p.official && (
        <div className="absolute top-2 right-2">
          <span title="Official Plugin"><Star size={12} className="text-kernel-400" /></span>
        </div>
      )}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0 pr-6">
          <div className="flex items-center gap-2">
            <Package size={14} className={p.enabled ? 'text-kernel-400' : 'text-gray-700'} />
            <h4 className="text-sm font-medium">{p.display_name}</h4>
            <span className="text-[10px] text-gray-600">v{p.version}</span>
          </div>
          <p className="text-xs text-gray-500 mt-1 line-clamp-2">{p.description}</p>
        </div>
        <button
          onClick={() => onToggle(p.name, p.enabled)}
          className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] transition-colors flex-shrink-0 ${
            p.enabled ? 'bg-red-900/30 text-red-400 hover:bg-red-900/50'
                      : 'bg-green-900/30 text-green-400 hover:bg-green-900/50'
          }`}
        >
          {p.enabled ? <XCircle size={12} /> : <CheckCircle2 size={12} />}
          {p.enabled ? 'Disable' : 'Enable'}
        </button>
      </div>

      {/* Skills */}
      {p.skills.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {p.skills.map(s => (
            <span key={s} className="text-[10px] bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded">{s}</span>
          ))}
        </div>
      )}

      {/* Agent targets */}
      {p.target_agents.length > 0 && (
        <div className="flex items-center gap-1 mt-2 text-[10px] text-gray-600">
          <Bot size={10} />
          {p.target_agents.join(', ')}
        </div>
      )}
    </div>
  )
}
