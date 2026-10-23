import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Chat from './pages/Chat'

export default function App() {
  return (
    <BrowserRouter>
      <div className="h-screen bg-gray-950 text-white overflow-hidden">
        <Routes>
          <Route path="*" element={<Chat />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
