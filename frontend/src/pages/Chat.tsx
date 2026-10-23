import { useEffect, useRef, useState } from 'react'
import Message from '../components/Message'
import { sendChat, listDocuments, uploadDocument, deleteDocument } from '../services/api'
import type { Document, ChatResponse } from '../services/api'

interface Msg {
  role: 'user' | 'bot'
  content: string
  data?: ChatResponse
}

const SUGGESTIONS = [
  'Summarize this document',
  'What are the key points?',
  'Explain the main topic',
  'List the important facts',
]

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [docs, setDocs] = useState<Document[]>([])
  const [selectedDocs, setSelectedDocs] = useState<string[]>([])
  const [showDocPicker, setShowDocPicker] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const refreshDocs = () =>
    listDocuments().then((r) => setDocs(r.data.filter((d) => d.status === 'ready')))

  useEffect(() => {
    refreshDocs()
    const interval = setInterval(refreshDocs, 4000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 180) + 'px'
  }, [input])

  const handleFile = async (file: File) => {
    setUploadError('')
    setUploading(true)
    try {
      await uploadDocument(file)
      await refreshDocs()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setUploadError(typeof msg === 'string' ? msg : 'Upload failed')
      setTimeout(() => setUploadError(''), 4000)
    } finally {
      setUploading(false)
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const handleDelete = async (id: string) => {
    await deleteDocument(id)
    setSelectedDocs((prev) => prev.filter((d) => d !== id))
    refreshDocs()
  }

  const toggleDoc = (id: string) =>
    setSelectedDocs((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]))

  const submit = async (text?: string) => {
    const q = (text ?? input).trim()
    if (!q || loading || q.length > 2000) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: q }])
    setLoading(true)
    try {
      const res = await sendChat(q, selectedDocs.length ? selectedDocs : undefined)
      setMessages((m) => [...m, { role: 'bot', content: res.data.answer, data: res.data }])
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: { message?: string } | string } } })?.response?.data?.detail
      const msg = typeof detail === 'object' ? detail?.message : detail
      setMessages((m) => [...m, { role: 'bot', content: `${msg ?? 'Something went wrong'}` }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div
      className="flex flex-col h-full relative"
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOver(false) }}
      onDrop={onDrop}
    >
      {/* Drag overlay */}
      {dragOver && (
        <div className="absolute inset-0 z-50 bg-[#0a0a0a]/90 border border-[#333] flex items-center justify-center pointer-events-none">
          <div className="text-center">
            <div className="w-12 h-12 rounded-xl border border-[#333] flex items-center justify-center mx-auto mb-3">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-[#666]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <p className="text-[#888] text-sm font-medium">Drop to upload</p>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-[#1a1a1a] shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded bg-white flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <span className="text-sm font-medium text-[#e8e8e8] tracking-tight">DocQA</span>
        </div>

        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
          {docs.length > 0 && (
            <div className="relative">
              <button
                onClick={() => setShowDocPicker(!showDocPicker)}
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md border border-[#222] text-[#888] hover:text-[#ccc] hover:border-[#333] transition-all"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                {selectedDocs.length ? `${selectedDocs.length} selected` : `${docs.length} doc${docs.length > 1 ? 's' : ''}`}
              </button>

              {showDocPicker && (
                <div className="absolute right-0 top-9 z-20 bg-[#111] border border-[#222] rounded-lg shadow-2xl p-1.5 w-64">
                  {docs.map((d) => (
                    <div key={d.id} className="flex items-center gap-2 px-2.5 py-2 rounded-md hover:bg-[#1a1a1a] group transition-colors">
                      <button onClick={() => toggleDoc(d.id)} className="flex items-center gap-2 flex-1 text-left">
                        <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center shrink-0 transition-colors ${selectedDocs.includes(d.id) ? 'bg-white border-white' : 'border-[#444]'}`}>
                          {selectedDocs.includes(d.id) && <svg xmlns="http://www.w3.org/2000/svg" className="w-2.5 h-2.5 text-black" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>}
                        </div>
                        <span className="text-xs text-[#aaa] truncate">{d.name}</span>
                      </button>
                      <button onClick={() => handleDelete(d.id)} className="opacity-0 group-hover:opacity-100 transition-opacity">
                        <svg xmlns="http://www.w3.org/2000/svg" className="w-3 h-3 text-[#555] hover:text-[#ff6b6b]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ))}
                  {selectedDocs.length > 0 && (
                    <button onClick={() => setSelectedDocs([])} className="w-full text-center text-xs text-[#555] hover:text-[#888] mt-1 pt-1.5 border-t border-[#1a1a1a] transition-colors">
                      Clear selection
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-white text-black font-medium hover:bg-[#e8e8e8] disabled:opacity-40 transition-all"
          >
            {uploading ? (
              <svg className="w-3 h-3 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            )}
            {uploading ? 'Uploading' : 'Upload'}
          </button>
          <input ref={fileInputRef} type="file" accept=".pdf,.txt,.docx,.md" className="hidden" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
        </div>
      </header>

      {/* Upload error */}
      {uploadError && (
        <div className="px-6 py-2 bg-[#1a0a0a] border-b border-[#2a1a1a] text-[#ff6b6b] text-xs">{uploadError}</div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto" onClick={() => setShowDocPicker(false)}>
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full px-4 text-center">
            <div className="w-10 h-10 rounded-xl border border-[#222] flex items-center justify-center mb-6">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-[#555]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h2 className="text-lg font-medium text-[#e8e8e8] mb-1.5">
              {docs.length > 0 ? 'What would you like to know?' : 'Start by uploading a document'}
            </h2>
            <p className="text-[#555] text-sm max-w-xs leading-relaxed">
              {docs.length > 0
                ? `${docs.length} document${docs.length > 1 ? 's' : ''} ready`
                : 'Drag & drop a file or click Upload'}
            </p>

            {docs.length > 0 && (
              <div className="grid grid-cols-2 gap-2 mt-8 max-w-sm w-full">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => submit(s)}
                    className="text-left px-3.5 py-2.5 rounded-lg border border-[#1e1e1e] text-xs text-[#666] hover:text-[#aaa] hover:border-[#2a2a2a] transition-all"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="max-w-2xl mx-auto px-4 py-8 space-y-8">
            {messages.map((m, i) => <Message key={i} msg={m} />)}
            {loading && (
              <div className="flex items-center gap-3">
                <div className="w-6 h-6 rounded border border-[#222] flex items-center justify-center shrink-0">
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-3 h-3 text-[#555]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 bg-[#444] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 bg-[#444] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 bg-[#444] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-4 pb-5 pt-2 shrink-0" onClick={() => setShowDocPicker(false)}>
        <div className="max-w-2xl mx-auto">
          <div className="flex items-end gap-2 bg-[#111] border border-[#1e1e1e] rounded-xl px-4 py-3 focus-within:border-[#2e2e2e] transition-colors">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything..."
              maxLength={2000}
              rows={1}
              className="flex-1 bg-transparent text-sm text-[#e8e8e8] placeholder-[#3a3a3a] resize-none focus:outline-none leading-6"
            />
            <button
              onClick={() => submit()}
              disabled={loading || !input.trim()}
              className="w-7 h-7 rounded-md bg-white hover:bg-[#e8e8e8] disabled:bg-[#1e1e1e] disabled:cursor-not-allowed flex items-center justify-center transition-all shrink-0"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5 text-black disabled:text-[#444]">
                <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
              </svg>
            </button>
          </div>
          <p className="text-center text-[10px] text-[#2a2a2a] mt-2 tracking-wide">ENTER TO SEND · DRAG & DROP TO UPLOAD</p>
        </div>
      </div>
    </div>
  )
}
