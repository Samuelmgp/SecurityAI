import { useState, useRef, type KeyboardEvent } from 'react'
import { Send, Paperclip, Loader2 } from 'lucide-react'

interface ChatInputProps {
  onSend: (content: string) => void
  disabled?: boolean
  placeholder?: string
}

export default function ChatInput({ onSend, disabled, placeholder }: ChatInputProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 180) + 'px'
  }

  return (
    <div className="border-t border-gray-800 bg-gray-950 px-4 py-3">
      <div className="flex items-end gap-2 bg-gray-900 border border-gray-700 focus-within:border-cyan-500/50 rounded-xl px-3 py-2 transition-colors">
        <button
          className="shrink-0 text-gray-600 hover:text-gray-400 transition-colors mb-1"
          title="Attach file (coming soon)"
          disabled
        >
          <Paperclip size={16} />
        </button>

        <textarea
          ref={textareaRef}
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          rows={1}
          disabled={disabled}
          placeholder={placeholder ?? 'Ask about secure development, pen-testing, or reverse engineering…'}
          className="flex-1 bg-transparent text-sm text-gray-200 placeholder-gray-600 resize-none outline-none py-1 min-h-[24px] max-h-[180px]"
        />

        <button
          onClick={handleSend}
          disabled={!value.trim() || disabled}
          className="shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-800 disabled:text-gray-600 text-white transition-colors mb-0.5"
          title="Send (Enter)"
        >
          {disabled
            ? <Loader2 size={14} className="animate-spin" />
            : <Send size={14} />
          }
        </button>
      </div>
      <p className="text-[10px] text-gray-700 mt-1.5 text-center">
        Shift+Enter for newline · Enter to send
      </p>
    </div>
  )
}
