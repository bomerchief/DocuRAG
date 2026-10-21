import { useRef, useState } from 'react'
import { uploadDocument } from '../services/api'

interface Props {
  onUploaded: () => void
}

export default function DocumentUpload({ onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  const handleFile = async (file: File) => {
    setError('')
    setUploading(true)
    try {
      await uploadDocument(file)
      onUploaded()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <div
      onDrop={onDrop}
      onDragOver={(e) => e.preventDefault()}
      onClick={() => inputRef.current?.click()}
      className="border-2 border-dashed border-gray-600 hover:border-blue-500 rounded-xl p-8 text-center cursor-pointer transition-colors"
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,.docx,.md"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      {uploading ? (
        <p className="text-blue-400">Uploading & processing...</p>
      ) : (
        <>
          <p className="text-gray-300">Drop a file or click to upload</p>
          <p className="text-gray-500 text-sm mt-1">PDF · DOCX · TXT · Markdown</p>
        </>
      )}
      {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
    </div>
  )
}
