import type { EvalRunSummary } from '../services/api'

interface Props {
  runs: EvalRunSummary[]
  onSelect: (id: string) => void
  selectedId?: string
}

const fmt = (v?: number | null) => (v == null ? '—' : v.toFixed(3))
const fmtMs = (v?: number | null) => (v == null ? '—' : `${v.toFixed(0)}ms`)

export default function EvaluationTable({ runs, onSelect, selectedId }: Props) {
  if (!runs.length) return (
    <div className="text-center py-10 text-gray-500">
      <p className="text-3xl mb-3">🧪</p>
      <p className="text-sm font-medium text-gray-400">No evaluation runs yet.</p>
      <p className="text-xs mt-2 text-gray-600">Upload documents and run your first evaluation to see:</p>
      <ul className="text-xs mt-2 text-gray-600 space-y-1">
        <li>• RAG quality metrics</li>
        <li>• Question-level results</li>
        <li>• Retrieved context inspection</li>
        <li>• Experiment comparisons</li>
      </ul>
    </div>
  )

  const bestRecall = Math.max(...runs.map((r) => r.recall_at_5 ?? 0))

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs text-left">
        <thead>
          <tr className="text-gray-400 border-b border-gray-700">
            <th className="py-2 pr-3">Run</th>
            <th className="py-2 pr-3">Dataset</th>
            <th className="py-2 pr-3">Chunk</th>
            <th className="py-2 pr-3">Overlap</th>
            <th className="py-2 pr-3">Top-K</th>
            <th className="py-2 pr-3">Threshold</th>
            <th className="py-2 pr-3">Prompt</th>
            <th className="py-2 pr-3">Faithfulness</th>
            <th className="py-2 pr-3">Correctness</th>
            <th className="py-2 pr-3">Recall@5</th>
            <th className="py-2 pr-3">Precision@5</th>
            <th className="py-2 pr-3">MRR</th>
            <th className="py-2 pr-3">Hallucination</th>
            <th className="py-2 pr-3">Latency</th>
            <th className="py-2 pr-3">Qs</th>
            <th className="py-2 pr-3">Date</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r, i) => {
            const isBest = (r.recall_at_5 ?? 0) === bestRecall && bestRecall > 0
            const dateStr = r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'
            return (
              <tr
                key={r.id}
                onClick={() => onSelect(r.id)}
                className={`border-b border-gray-800 cursor-pointer hover:bg-gray-750 transition-colors ${
                  selectedId === r.id ? 'bg-gray-800 ring-1 ring-inset ring-blue-500/40' : ''
                } ${isBest ? 'ring-1 ring-inset ring-green-500/30' : ''}`}
              >
                <td className="py-2 pr-3 font-mono text-gray-400">
                  {isBest && <span className="text-green-400 mr-1">★</span>}
                  exp-{String(i + 1).padStart(3, '0')}
                </td>
                <td className="py-2 pr-3 text-gray-300 max-w-[120px] truncate">{r.dataset_name}</td>
                <td className="py-2 pr-3">{r.chunk_size}</td>
                <td className="py-2 pr-3">{r.chunk_overlap}</td>
                <td className="py-2 pr-3">{r.top_k}</td>
                <td className="py-2 pr-3">{r.similarity_threshold}</td>
                <td className="py-2 pr-3 text-purple-400">{r.prompt_version}</td>
                <td className="py-2 pr-3 text-green-400">{fmt(r.faithfulness)}</td>
                <td className="py-2 pr-3 text-blue-400">{fmt(r.answer_correctness)}</td>
                <td className={`py-2 pr-3 ${isBest ? 'text-green-400 font-bold' : ''}`}>{fmt(r.recall_at_5)}</td>
                <td className="py-2 pr-3">{fmt(r.precision_at_5)}</td>
                <td className="py-2 pr-3">{fmt(r.mrr)}</td>
                <td className="py-2 pr-3 text-red-400">{fmt(r.hallucination_rate)}</td>
                <td className="py-2 pr-3 text-gray-400">{fmtMs(r.avg_latency_ms)}</td>
                <td className="py-2 pr-3 text-gray-400">{r.num_questions}</td>
                <td className="py-2 pr-3 text-gray-500">{dateStr}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
