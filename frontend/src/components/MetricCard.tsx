interface Props {
  label: string
  value: string | number | null | undefined
  sub?: string
  color?: 'green' | 'blue' | 'red' | 'yellow' | 'purple'
}

const colorMap = {
  green: 'text-green-400',
  blue: 'text-blue-400',
  red: 'text-red-400',
  yellow: 'text-yellow-400',
  purple: 'text-purple-400',
}

export default function MetricCard({ label, value, sub, color = 'blue' }: Props) {
  const display = value == null ? '—' : typeof value === 'number' ? value.toFixed(3) : value
  return (
    <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${colorMap[color]}`}>{display}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  )
}
