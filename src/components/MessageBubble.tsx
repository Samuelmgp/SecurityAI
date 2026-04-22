import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Shield, User, BookOpen, Copy, Check } from 'lucide-react'
import { useState } from 'react'
import type { Message } from '../types'

interface MessageBubbleProps {
  message: Message
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <button
      onClick={copy}
      className="absolute top-2 right-2 p-1.5 rounded bg-gray-700 hover:bg-gray-600 text-gray-400 hover:text-white transition-colors"
      title="Copy"
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
    </button>
  )
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isAssistant = message.role === 'assistant'

  return (
    <div className={`flex gap-3 ${isAssistant ? '' : 'flex-row-reverse'}`}>
      {/* Avatar */}
      <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isAssistant
          ? 'bg-cyan-500/10 border border-cyan-500/30 text-cyan-400'
          : 'bg-gray-700 border border-gray-600 text-gray-300'
      }`}>
        {isAssistant ? <Shield size={14} /> : <User size={14} />}
      </div>

      {/* Bubble */}
      <div className={`flex flex-col gap-1.5 max-w-[80%] ${isAssistant ? '' : 'items-end'}`}>
        <div className={`rounded-xl px-4 py-3 text-sm leading-relaxed ${
          isAssistant
            ? 'bg-gray-900 border border-gray-800 text-gray-200'
            : 'bg-cyan-600/20 border border-cyan-500/30 text-gray-100'
        }`}>
          <ReactMarkdown
            components={{
              code({ className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '')
                const code = String(children).replace(/\n$/, '')
                if (match) {
                  return (
                    <div className="relative mt-2 mb-1 rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-950 border-b border-gray-800">
                        <span className="text-[10px] text-gray-500 uppercase tracking-wider">{match[1]}</span>
                        <CopyButton text={code} />
                      </div>
                      <SyntaxHighlighter
                        style={oneDark}
                        language={match[1]}
                        PreTag="div"
                        customStyle={{ margin: 0, borderRadius: 0, fontSize: '0.78rem' }}
                      >
                        {code}
                      </SyntaxHighlighter>
                    </div>
                  )
                }
                return (
                  <code className="bg-gray-800 text-cyan-300 px-1.5 py-0.5 rounded text-xs font-mono" {...props}>
                    {children}
                  </code>
                )
              },
              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-2">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 mb-2">{children}</ol>,
              li: ({ children }) => <li className="text-gray-300">{children}</li>,
              strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
              h3: ({ children }) => <h3 className="text-white font-semibold mt-3 mb-1">{children}</h3>,
              blockquote: ({ children }) => (
                <blockquote className="border-l-2 border-cyan-500/50 pl-3 text-gray-400 italic my-2">
                  {children}
                </blockquote>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {message.sources.map((src, i) => (
              <span
                key={i}
                className="flex items-center gap-1 text-[10px] text-gray-500 bg-gray-900 border border-gray-800 rounded px-1.5 py-0.5"
              >
                <BookOpen size={9} />
                {src.book}{src.page ? ` p.${src.page}` : ''}
              </span>
            ))}
          </div>
        )}

        <span className="text-[10px] text-gray-600 px-1">
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  )
}
