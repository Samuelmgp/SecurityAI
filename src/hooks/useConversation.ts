import { useState, useCallback } from 'react'
import type { Conversation, Message, Category, Source } from '../types'

function generateId(): string {
  return Math.random().toString(36).slice(2, 11)
}

function getTitle(content: string): string {
  return content.length > 40 ? content.slice(0, 40) + '…' : content
}

export function useConversation() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)

  const activeConversation = conversations.find(c => c.id === activeId) ?? null

  const createConversation = useCallback((category: Category = 'general'): string => {
    const id = generateId()
    const now = new Date()
    setConversations(prev => [
      {
        id,
        title: 'New conversation',
        messages: [],
        category,
        createdAt: now,
        updatedAt: now,
      },
      ...prev,
    ])
    setActiveId(id)
    return id
  }, [])

  const appendMessage = useCallback((conversationId: string, message: Omit<Message, 'id' | 'timestamp'>) => {
    const id = generateId()
    const timestamp = new Date()
    setConversations(prev =>
      prev.map(c => {
        if (c.id !== conversationId) return c
        const messages = [...c.messages, { ...message, id, timestamp }]
        return {
          ...c,
          messages,
          title: c.messages.length === 0 && message.role === 'user'
            ? getTitle(message.content)
            : c.title,
          updatedAt: timestamp,
        }
      })
    )
    return id
  }, [])

  // Mutate an existing message in-place — used to stream assistant tokens
  const updateLastAssistantMessage = useCallback(
    (conversationId: string, messageId: string, content: string, sources: Source[]) => {
      setConversations(prev =>
        prev.map(c => {
          if (c.id !== conversationId) return c
          return {
            ...c,
            messages: c.messages.map(m =>
              m.id === messageId ? { ...m, content, sources } : m
            ),
          }
        })
      )
    },
    [],
  )

  const deleteConversation = useCallback((id: string) => {
    setConversations(prev => prev.filter(c => c.id !== id))
    setActiveId(prev => (prev === id ? null : prev))
  }, [])

  return {
    conversations,
    activeConversation,
    activeId,
    setActiveId,
    createConversation,
    appendMessage,
    updateLastAssistantMessage,
    deleteConversation,
  }
}
