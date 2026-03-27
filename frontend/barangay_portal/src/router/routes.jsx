import { lazy } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'
import AuthLayout from '../components/layout/AuthLayout'
import MainLayout from '../components/layout/MainLayout'

const LoginPage             = lazy(() => import('../pages/LoginPage'))
const DashboardPage         = lazy(() => import('../pages/DashboardPage'))
const AdminsPage            = lazy(() => import('../pages/users/AdminsPage'))
const StaffPage             = lazy(() => import('../pages/users/StaffPage'))
const ResidentsPage         = lazy(() => import('../pages/residents/ResidentsPage'))
const ResidentDetailPage    = lazy(() => import('../pages/residents/ResidentDetailPage'))
const ChangePasswordPage    = lazy(() => import('../pages/ChangePasswordPage'))
const UnauthorizedPage      = lazy(() => import('../pages/UnauthorizedPage'))
const StaffDetailPage       = lazy(() => import('../pages/users/StaffDetailPage'))

// Profiling
const ProfilingPage         = lazy(() => import('../pages/profiling/ProfilingPage'))
const SurveyWizard          = lazy(() => import('../pages/profiling/SurveyWizard'))
const HouseholdComparison   = lazy(() => import('../pages/profiling/HouseholdComparison'))
const ConceptSearch         = lazy(() => import('../pages/profiling/ConceptSearch'))
const ReportBuilder         = lazy(() => import('../pages/profiling/ReportBuilder'))
const SchemaBuilderPage     = lazy(() => import('../pages/profiling/SchemaBuilderPage'))

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

          // SUPER_ADMIN only
          {
            element: <ProtectedRoute allowedRoles={['SUPER_ADMIN']} />,
            children: [
              { path: 'users/admins', element: <AdminsPage /> },
            ],
          },

          // SUPER_ADMIN or ADMIN (with perm_manage_staff checked in the page)
          {
            element: <ProtectedRoute allowedRoles={['SUPER_ADMIN', 'ADMIN']} />,
            children: [
              { path: 'users/staff',      element: <StaffPage /> },
              { path: 'users/staff/:id',  element: <StaffDetailPage /> },
            ],
          },

          // Residents
          { path: 'residents',     element: <ResidentsPage /> },
          { path: 'residents/:id', element: <ResidentDetailPage /> },

          // Profiling — all authenticated staff
          { path: 'profiling',            element: <ProfilingPage /> },
          { path: 'profiling/wizard',     element: <SurveyWizard /> },
          { path: 'profiling/comparison', element: <HouseholdComparison /> },
          { path: 'profiling/concepts',   element: <ConceptSearch /> },
          { path: 'profiling/reports',    element: <ReportBuilder /> },

          // Profiling — admin-only schema builder
          {
            element: <ProtectedRoute allowedRoles={['SUPER_ADMIN', 'ADMIN']} />,
            children: [
              { path: 'profiling/schemas', element: <SchemaBuilderPage /> },
            ],
          },

          // Account
          { path: 'change-password', element: <ChangePasswordPage /> },

          { path: 'unauthorized', element: <UnauthorizedPage /> },
        ],
      },
    ],
  },
])

export default router
