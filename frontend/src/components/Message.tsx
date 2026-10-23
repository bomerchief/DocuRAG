import { useState } from 'react'
import SourceCard from './SourceCard'
import type { ChatResponse } from '../services/api'

interface Props {
  msg: { role: 'user' | 'bot'; content: string; data?: ChatResponse }
}

export default function Message({ msg }: Props) {
  const [showSources, setShowSources] = useState(false)
  const [showWebSources, setShowWebSources] = useState(false)
  const isUser = msg.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <p className="max-w-lg text-sm text-[#e8e8e8] bg-[#161616] border border-[#222] px-4 py-2.5 rounded-xl rounded-br-sm leading-relaxed whitespace-pre-wrap">
          {msg.content}
        </p>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3">
      <div className="w-6 h-6 rounded border border-[#222] flex items-center justify-center shrink-0 mt-0.5">
        <svg xmlns="http://www.w3.org/2000/svg" className="w-3 h-3 text-[#555]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-sm text-[#d0d0d0] leading-relaxed whitespace-pre-wrap">{msg.content}</p>

        {msg.data && (
          <div className="flex flex-wrap items-center gap-2.5 mt-3">
            <span className="text-[10px] text-[#333] tracking-wide">{msg.data.metrics.total_latency_ms.toFixed(0)}ms</span>

            {msg.data.sources.length > 0 && (
              <button
                onClick={() => setShowSources(!showSources)}
                className="text-[10px] text-[#444] hover:text-[#888] tracking-wide transition-colors flex items-center gap-1"
              >
                {showSources ? '−' : '+'} {msg.data.sources.length} source{msg.data.sources.length > 1 ? 's' : ''}
              </button>
            )}

            {msg.data.web_sources?.length > 0 && (
              <button
                onClick={() => setShowWebSources(!showWebSources)}
                className="text-[10px] text-[#444] hover:text-[#888] tracking-wide transition-colors flex items-center gap-1"
              >
                {showWebSources ? '−' : '+'} {msg.data.web_sources.length} web
              </button>
            )}
          </div>
        )}

        {showSources && msg.data?.sources && msg.data.sources.length > 0 && (
          <div className="mt-3 space-y-1.5">
            {msg.data.sources.map((s, i) => (
              <SourceCard key={s.chunk_id} source={s} index={i + 1} />
            ))}
          </div>
        )}

        {showWebSources && msg.data?.web_sources && msg.data.web_sources.length > 0 && (
          <div className="mt-3 space-y-1.5">
            {msg.data.web_sources.map((w, i) => (
              <div key={i} className="border border-[#1e1e1e] rounded-lg p-3">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-xs text-[#aaa] font-medium leading-snug">{w.title}</span>
                  <a href={w.url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-[#444] hover:text-[#888] shrink-0 transition-colors">↗</a>
                </div>
                <p className="text-[10px] text-[#333] mt-0.5 truncate">{w.url}</p>
                <p className="text-xs text-[#666] mt-2 leading-relaxed">{w.snippet}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
