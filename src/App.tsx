import { useState, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'
import { useConversation } from './hooks/useConversation'
import type { Category } from './types'

export default function App() {
  const [selectedCategory, setSelectedCategory] = useState<Category>('general')
  const [isLoading, setIsLoading] = useState(false)

  const {
    conversations,
    activeConversation,
    activeId,
    setActiveId,
    createConversation,
    appendMessage,
    deleteConversation,
  } = useConversation()

  const handleSend = useCallback(async (content: string) => {
    let convId = activeId
    if (!convId) {
      convId = createConversation(selectedCategory)
    }

    appendMessage(convId, { role: 'user', content })
    setIsLoading(true)

    // Placeholder — will be replaced with actual LLM API call
    await new Promise(res => setTimeout(res, 1200))
    appendMessage(convId, {
      role: 'assistant',
      content: `I'm the SecurityAI assistant. The LLM backend isn't connected yet — this is the frontend scaffold.\n\nYou asked:\n> ${content}\n\nOnce the backend is wired up, I'll answer using knowledge extracted from **Gray Hat Hacking** and **Reversing: Secrets of Reverse Engineering**.`,
      sources: [
        { book: 'Gray Hat Hacking', chapter: 'Ch. 1', page: 3 },
      ],
    })
    setIsLoading(false)
  }, [activeId, selectedCategory, createConversation, appendMessage])

  const handleNew = useCallback((category: Category = selectedCategory) => {
    createConversation(category)
  }, [selectedCategory, createConversation])

  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
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
