import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Chat from './pages/Chat'
import Documents from './pages/Documents'
import Evaluation from './pages/Evaluation'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
    isActive ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'
  }`

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden">
        {/* Sidebar */}
        <aside className="w-52 bg-gray-900 border-r border-gray-800 flex flex-col p-4 shrink-0">
          <div className="mb-6">
            <h1 className="text-sm font-bold text-white">Document Q&A</h1>
            <p className="text-xs text-gray-500 mt-0.5">RAG + Evaluation</p>
          </div>
          <nav className="space-y-1">
            <NavLink to="/" end className={navClass}>💬 Chat</NavLink>
            <NavLink to="/documents" className={navClass}>📄 Documents</NavLink>
            <NavLink to="/evaluation" className={navClass}>📊 Evaluation</NavLink>
          </nav>
        </aside>

        {/* Main */}
        <main className="flex-1 overflow-y-auto bg-gray-950">
          <Routes>
            <Route path="/" element={<Chat />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/evaluation" element={<Evaluation />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
