import { StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { ToastProvider } from './context/ToastContext.jsx'
import Spinner from './components/ui/Spinner.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ToastProvider>
      <Suspense
        fallback={
          <div className="flex items-center justify-center h-screen bg-slate-50">
            <Spinner size="lg" />
          </div>
        }
      >
        <App />
      </Suspense>
    </ToastProvider>
  </StrictMode>,
)
