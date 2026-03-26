import { lazy } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'
import AuthLayout from '../components/layout/AuthLayout'
import MainLayout from '../components/layout/MainLayout'

const LoginPage           = lazy(() => import('../pages/LoginPage'))
const DashboardPage       = lazy(() => import('../pages/DashboardPage'))
const AdminsPage          = lazy(() => import('../pages/users/AdminsPage'))
const StaffPage           = lazy(() => import('../pages/users/StaffPage'))
const ResidentsPage       = lazy(() => import('../pages/residents/ResidentsPage'))
const ResidentDetailPage  = lazy(() => import('../pages/residents/ResidentDetailPage'))
const ChangePasswordPage  = lazy(() => import('../pages/ChangePasswordPage'))

const router = createBrowserRouter([
  {
    element: <AuthLayout />,
    children: [
      { path: '/login', element: <LoginPage /> },
    ],
  },
  {
    path: '/',
    element: <ProtectedRoute />,
    children: [
      {
        element: <MainLayout />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: 'dashboard', element: <DashboardPage /> },

          // User management
          { path: 'users/admins', element: <AdminsPage /> },
          { path: 'users/staff',  element: <StaffPage /> },

          // Residents
          { path: 'residents',     element: <ResidentsPage /> },
          { path: 'residents/:id', element: <ResidentDetailPage /> },

          // Account
          { path: 'change-password', element: <ChangePasswordPage /> },
        ],
      },
    ],
  },
])

export default router
