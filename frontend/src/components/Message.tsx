import { useState } from 'react'
import SourceCard from './SourceCard'
import type { ChatResponse } from '../services/api'

interface Props {
  msg: { role: 'user' | 'bot'; content: string; data?: ChatResponse }
}

export default function Message({ msg }: Props) {
  const [showSources, setShowSources] = useState(true)
  const isUser = msg.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-3xl ${isUser ? 'bg-blue-700 text-white' : 'bg-gray-800 text-gray-100'} rounded-2xl px-4 py-3`}>
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>

        {msg.data && (
          <div className="mt-3 border-t border-gray-700 pt-2">
            <div className="flex gap-4 text-xs text-gray-400">
              <span>⏱ {msg.data.metrics.total_latency_ms.toFixed(0)}ms</span>
              <span>📄 {msg.data.metrics.chunks_retrieved} chunks retrieved</span>
            </div>

            {msg.data.sources.length > 0 && (
              <div className="mt-2">
                <button
                  onClick={() => setShowSources(!showSources)}
                  className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                >
                  {showSources ? '▲ Hide' : '▼ Show'} Sources ({msg.data.sources.length})
                </button>
                {showSources && (
                  <div className="mt-2 space-y-2">
                    {msg.data.sources.map((s, i) => (
                      <SourceCard key={s.chunk_id} source={s} index={i + 1} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {msg.data.sources.length === 0 && (
              <p className="text-xs text-gray-600 mt-1 italic">No source documents retrieved.</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
