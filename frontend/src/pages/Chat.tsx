import { useEffect, useRef, useState } from 'react'
import Message from '../components/Message'
import { sendChat, listDocuments } from '../services/api'
import type { Document, ChatResponse } from '../services/api'

interface Msg {
  role: 'user' | 'bot'
  content: string
  data?: ChatResponse
}

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [docs, setDocs] = useState<Document[]>([])
  const [selectedDocs, setSelectedDocs] = useState<string[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    listDocuments().then((r) => setDocs(r.data.filter((d) => d.status === 'ready')))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const toggleDoc = (id: string) =>
    setSelectedDocs((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]))

  const MAX_QUESTION_LENGTH = 2000

  const submit = async () => {
    const q = input.trim()
    if (!q || loading) return
    if (q.length > MAX_QUESTION_LENGTH) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: q }])
    setLoading(true)
    try {
      const res = await sendChat(q, selectedDocs.length ? selectedDocs : undefined)
      setMessages((m) => [...m, { role: 'bot', content: res.data.answer, data: res.data }])
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: { message?: string } | string } } })?.response?.data?.detail
      const msg = typeof detail === 'object' ? detail?.message : detail
      setMessages((m) => [...m, { role: 'bot', content: `Error: ${msg ?? 'Something went wrong'}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-gray-800">
        <h1 className="text-lg font-semibold">Document Q&A</h1>
        {docs.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {docs.map((d) => (
              <button
                key={d.id}
                onClick={() => toggleDoc(d.id)}
                className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                  selectedDocs.includes(d.id)
                    ? 'bg-blue-600 border-blue-500 text-white'
                    : 'border-gray-600 text-gray-400 hover:border-gray-400'
                }`}
              >
                {d.name}
              </button>
            ))}
          </div>
        )}
        {docs.length === 0 && (
          <p className="text-gray-500 text-sm mt-1">Upload documents to get started.</p>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-600 mt-20">
            <p className="text-4xl mb-3">💬</p>
            <p>Ask a question about your documents</p>
          </div>
        )}
        {messages.map((m, i) => (
          <Message key={i} msg={m} />
        ))}
        {loading && (
          <div className="flex justify-start mb-4">
            <div className="bg-gray-800 rounded-2xl px-4 py-3 text-gray-400 text-sm animate-pulse">
              Thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-4 border-t border-gray-800">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && submit()}
              placeholder="Ask a question..."
              maxLength={2000}
              className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-blue-500"
            />
            {input.length > 1800 && (
              <span className={`absolute right-3 top-2 text-xs ${
                input.length > 2000 ? 'text-red-400' : 'text-yellow-400'
              }`}>
                {input.length}/2000
              </span>
            )}
          </div>
          <button
            onClick={submit}
            disabled={loading || !input.trim() || input.length > 2000}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 px-4 py-2 rounded-xl text-sm font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
