import { Shield, Plus, MessageSquare, Trash2, ChevronRight, Network, Code2, Bug, Search, BookOpen } from 'lucide-react'
import type { Category, CategoryMeta, Conversation } from '../types'

const CATEGORIES: CategoryMeta[] = [
  { id: 'general',            label: 'General',             description: 'Open-ended security queries' },
  { id: 'secure-dev',         label: 'Secure Development',  description: 'Hardening & SAST guidance' },
  { id: 'pen-testing',        label: 'Pen Testing',         description: 'Exploitation & tooling' },
  { id: 'reverse-engineering',label: 'Reverse Engineering',  description: 'Binary analysis & RE' },
  { id: 'network-security',   label: 'Network Security',    description: 'Protocols, firewalls & VPNs' },
]

const CATEGORY_ICONS: Record<Category, React.ReactNode> = {
  'general':             <BookOpen size={14} />,
  'secure-dev':          <Code2 size={14} />,
  'pen-testing':         <Bug size={14} />,
  'reverse-engineering': <Search size={14} />,
  'network-security':    <Network size={14} />,
}

interface SidebarProps {
  conversations: Conversation[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: (category?: Category) => void
  onDelete: (id: string) => void
  selectedCategory: Category
  onCategoryChange: (c: Category) => void
}

export default function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  selectedCategory,
  onCategoryChange,
}: SidebarProps) {
  return (
    <aside className="flex flex-col w-64 shrink-0 bg-gray-950 border-r border-gray-800 h-screen">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 py-4 border-b border-gray-800">
        <Shield className="text-cyan-400 shrink-0" size={22} />
        <span className="font-semibold text-white tracking-wide text-sm">SecurityAI</span>
      </div>

      {/* New chat button */}
      <div className="px-3 pt-3 pb-2">
        <button
          onClick={() => onNew(selectedCategory)}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/20 hover:border-cyan-500/40 text-cyan-400 text-sm font-medium transition-colors"
        >
          <Plus size={15} />
          New conversation
        </button>
      </div>

      {/* Category filter */}
      <div className="px-3 pb-2">
        <p className="text-[10px] uppercase tracking-widest text-gray-500 px-1 mb-1.5">Category</p>
        <div className="space-y-0.5">
          {CATEGORIES.map(cat => (
            <button
              key={cat.id}
              onClick={() => onCategoryChange(cat.id)}
              className={`flex items-center gap-2 w-full px-2.5 py-1.5 rounded-md text-xs transition-colors ${
                selectedCategory === cat.id
                  ? 'bg-gray-800 text-cyan-400'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-900'
              }`}
            >
              <span className="shrink-0">{CATEGORY_ICONS[cat.id]}</span>
              {cat.label}
              {selectedCategory === cat.id && <ChevronRight size={12} className="ml-auto" />}
            </button>
          ))}
        </div>
      </div>

      {/* Conversation history */}
      <div className="flex-1 overflow-y-auto px-3 pb-3 min-h-0">
        <p className="text-[10px] uppercase tracking-widest text-gray-500 px-1 mb-1.5">History</p>
        {conversations.length === 0 ? (
          <p className="text-xs text-gray-600 px-2 py-2">No conversations yet</p>
        ) : (
          <ul className="space-y-0.5">
            {conversations.map(conv => (
              <li key={conv.id}>
                <button
                  onClick={() => onSelect(conv.id)}
                  className={`group flex items-center gap-2 w-full px-2.5 py-2 rounded-md text-left text-xs transition-colors ${
                    activeId === conv.id
                      ? 'bg-gray-800 text-white'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-gray-900'
                  }`}
                >
                  <MessageSquare size={12} className="shrink-0" />
                  <span className="flex-1 truncate">{conv.title}</span>
                  <button
                    onClick={e => { e.stopPropagation(); onDelete(conv.id) }}
                    className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 transition-all"
                  >
                    <Trash2 size={11} />
                  </button>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-800">
        <p className="text-[10px] text-gray-600">Powered by local LLM</p>
        <p className="text-[10px] text-gray-700">Gray Hat Hacking · RE Secrets</p>
      </div>
    </aside>
  )
}
