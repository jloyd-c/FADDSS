import useAuthStore from '../store/authStore'

export default function DashboardPage() {
  const { user } = useAuthStore()

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-2">My Dashboard</h1>
      <p className="text-gray-500">Welcome, {user?.full_name || user?.email}</p>
    </div>
  )
}
