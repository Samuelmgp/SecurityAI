import { useState, useCallback, useRef } from 'react'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'
import { useConversation } from './hooks/useConversation'
import type { Category, Source } from './types'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const REQUEST_TIMEOUT_MS = 60_000

export default function App() {
  const [selectedCategory, setSelectedCategory] = useState<Category>('general')
  const [isLoading, setIsLoading] = useState(false)
  const activeConvIdRef = useRef<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const {
    conversations,
    activeConversation,
    activeId,
    setActiveId,
    createConversation,
    appendMessage,
    updateLastAssistantMessage,
    deleteConversation,
  } = useConversation()

  const handleSend = useCallback(async (content: string) => {
    // Cancel any in-flight request before starting a new one
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

    let convId = activeId ?? activeConvIdRef.current
    if (!convId) {
      convId = createConversation(selectedCategory)
      activeConvIdRef.current = convId
    }

    const history = (activeConversation?.messages ?? []).map(m => ({
      role: m.role,
      content: m.content,
    }))

    appendMessage(convId, { role: 'user', content })
    const assistantMsgId = appendMessage(convId, { role: 'assistant', content: '' })
    setIsLoading(true)

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: content, history, category: selectedCategory }),
        signal: controller.signal,
      })

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''
      let sources: Source[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value, { stream: true })
        for (const line of text.split('\n')) {
          if (!line.startsWith('data: ')) continue
          try {
            const payload = JSON.parse(line.slice(6))

            if (payload.error) {
              accumulated += `\n\n_Error: ${payload.error}_`
              updateLastAssistantMessage(convId, assistantMsgId, accumulated, sources)
              break
            }

            if (payload.token) {
              accumulated += payload.token
              updateLastAssistantMessage(convId, assistantMsgId, accumulated, sources)
            }

            if (payload.done && payload.sources) {
              sources = (payload.sources as Array<{ book: string; page?: number }>).map(s => ({
                book: s.book,
                chapter: '',
                page: s.page,
              }))
              updateLastAssistantMessage(convId, assistantMsgId, accumulated, sources)
            }
          } catch {
            // malformed SSE line — skip
          }
        }
      }
    } catch (err) {
      const isTimeout = err instanceof DOMException && err.name === 'AbortError'
      const msg = isTimeout
        ? '_Request timed out after 60 seconds. The model may still be warming up — please try again in a moment._'
        : `_Could not reach the backend: ${err instanceof Error ? err.message : 'Unknown error'}. Make sure the backend is running._`
      updateLastAssistantMessage(convId, assistantMsgId, msg, [])
    } finally {
      clearTimeout(timeoutId)
      setIsLoading(false)
    }
  }, [activeId, activeConversation, selectedCategory, createConversation, appendMessage, updateLastAssistantMessage])

  const handleNew = useCallback((category: Category = selectedCategory) => {
    abortRef.current?.abort()
    const id = createConversation(category)
    activeConvIdRef.current = id
  }, [selectedCategory, createConversation])

  const handleSelect = useCallback((id: string) => {
    setActiveId(id)
    activeConvIdRef.current = id
  }, [setActiveId])

  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={handleSelect}
        onNew={handleNew}
        onDelete={deleteConversation}
        selectedCategory={selectedCategory}
        onCategoryChange={setSelectedCategory}
      />
      <main className="flex flex-1 min-w-0">
        <ChatWindow
          conversation={activeConversation}
          onSend={handleSend}
          isLoading={isLoading}
          category={selectedCategory}
        />
      </main>
    </div>
  )
}
