import { useEffect, useRef } from 'react'
import { Shield, Bug, Code2, Network, Search, BookOpen } from 'lucide-react'
import MessageBubble from './MessageBubble'
import ChatInput from './ChatInput'
import type { Conversation, Category, Message } from '../types'

const CATEGORY_PROMPTS: Record<Category, { icon: React.ReactNode; headline: string; starters: string[] }> = {
  'general': {
    icon: <BookOpen size={28} />,
    headline: 'SecurityAI Assistant',
    starters: [
      'What are the OWASP Top 10 vulnerabilities?',
      'Explain the principle of least privilege',
      'How do I set up a secure CI/CD pipeline?',
    ],
  },
  'secure-dev': {
    icon: <Code2 size={28} />,
    headline: 'Secure Development',
    starters: [
      'How do I prevent SQL injection in Python?',
      'Explain input validation best practices',
      'How should I store passwords securely?',
    ],
  },
  'pen-testing': {
    icon: <Bug size={28} />,
    headline: 'Penetration Testing',
    starters: [
      'Walk me through a basic recon methodology',
      'Explain the Metasploit exploitation workflow',
      'How do privilege escalation attacks work on Linux?',
    ],
  },
  'reverse-engineering': {
    icon: <Search size={28} />,
    headline: 'Reverse Engineering',
    starters: [
      'How do I analyze a binary with Ghidra?',
      'Explain x86 calling conventions',
      'What are common anti-debugging techniques?',
    ],
  },
  'network-security': {
    icon: <Network size={28} />,
    headline: 'Network Security',
    starters: [
      'How does a man-in-the-middle attack work?',
      'Explain TLS handshake security considerations',
      'What tools are used for network packet analysis?',
    ],
  },
}

interface ChatWindowProps {
  conversation: Conversation | null
  onSend: (content: string) => void
  isLoading: boolean
  category: Category
}

export default function ChatWindow({ conversation, onSend, isLoading, category }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const meta = CATEGORY_PROMPTS[category]

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation?.messages])

  const messages: Message[] = conversation?.messages ?? []

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Header */}
      <div className="flex items-center gap-2.5 px-6 py-3.5 border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm">
        <Shield size={16} className="text-cyan-400" />
        <span className="text-sm font-medium text-gray-300">
          {conversation ? conversation.title : meta.headline}
        </span>
        <span className="ml-auto text-xs text-gray-600">
          {messages.length > 0 ? `${messages.length} message${messages.length > 1 ? 's' : ''}` : ''}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center gap-6 pb-16">
            <div className="text-cyan-400/50">{meta.icon}</div>
            <div>
              <h2 className="text-lg font-semibold text-gray-300 mb-1">{meta.headline}</h2>
              <p className="text-sm text-gray-600 max-w-xs">
                Grounded in curated security textbooks. Ask anything about the topic above.
              </p>
            </div>
            <div className="grid gap-2 w-full max-w-sm">
              {meta.starters.map((s, i) => (
                <button
                  key={i}
                  onClick={() => onSend(s)}
                  className="text-left text-sm text-gray-400 hover:text-gray-200 bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-gray-700 rounded-lg px-4 py-2.5 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map(msg => (
            <MessageBubble key={msg.id} message={msg} />
          ))
        )}

        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full flex items-center justify-center bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shrink-0">
              <Shield size={14} />
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
              <div className="flex gap-1 items-center h-4">
                <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <ChatInput onSend={onSend} disabled={isLoading} />
    </div>
  )
}
