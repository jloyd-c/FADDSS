import { useNavigate } from 'react-router-dom'
import { ShieldOff } from 'lucide-react'

export default function UnauthorizedPage() {
  const navigate = useNavigate()
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-4 text-center">
      <ShieldOff size={40} className="text-red-400" />
      <div>
        <h2 className="text-lg font-bold text-gray-800">Access Denied</h2>
        <p className="text-sm text-gray-500 mt-1">You don't have permission to view this page.</p>
      </div>
      <button
        onClick={() => navigate('/dashboard')}
        className="px-4 py-2 text-sm font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
      >
        Go to Dashboard
      </button>
    </div>
  )
}
