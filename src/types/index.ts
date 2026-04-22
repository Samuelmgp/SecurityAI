export type MessageRole = 'user' | 'assistant'

export interface Source {
  book: string
  chapter: string
  page?: number
}

export interface Message {
  id: string
  role: MessageRole
  content: string
  timestamp: Date
  sources?: Source[]
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  category: Category
  createdAt: Date
  updatedAt: Date
}

export type Category =
  | 'secure-dev'
  | 'pen-testing'
  | 'reverse-engineering'
  | 'network-security'
  | 'general'

export interface CategoryMeta {
  id: Category
  label: string
  description: string
}
