import { useState } from 'react'
import type { Source } from '../services/api'

interface Props {
  source: Source
  index: number
}

export default function SourceCard({ source, index }: Props) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-gray-400 font-mono text-xs">[{index}]</span>
          <span className="text-blue-300 font-medium">{source.document}</span>
          <span className="text-gray-400">· Page {source.page}</span>
          <span className="text-green-400 text-xs">score: {source.score.toFixed(3)}</span>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-gray-400 hover:text-white text-xs"
        >
          {expanded ? 'Hide' : 'View'}
        </button>
      </div>
      {source.section && (
        <p className="text-gray-500 text-xs mt-1">§ {source.section}</p>
      )}
      {expanded && (
        <p className="mt-2 text-gray-300 text-xs leading-relaxed border-t border-gray-700 pt-2">
          {source.snippet}
        </p>
      )}
    </div>
  )
}
