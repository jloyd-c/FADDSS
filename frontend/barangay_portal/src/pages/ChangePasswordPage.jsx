import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, KeyRound, CheckCircle } from 'lucide-react'
import axiosInstance from '../api/axiosInstance'
import useAuthStore from '../store/authStore'
import { useToast } from '../context/ToastContext'
import { Card, CardBody } from '../components/ui/Card'

function PasswordField({ label, name, value, onChange, error, show, onToggle }) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <div className="relative">
        <input
          type={show ? 'text' : 'password'}
          name={name}
          value={value}
          onChange={onChange}
          required
          className={`w-full rounded-lg border px-3 py-2.5 pr-10 text-sm outline-none transition-colors
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500
            ${error ? 'border-red-400 bg-red-50' : 'border-gray-300 hover:border-gray-400'}`}
        />
        <button
          type="button"
          onClick={onToggle}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
        >
          {show ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}

export default function ChangePasswordPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const { user, setUser } = useAuthStore()
  const mustChange = user?.must_change_password

  const [form, setForm] = useState({ old_password: '', new_password: '', confirm_password: '' })
  const [show, setShow] = useState({ old: false, new: false, confirm: false })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState(false)

  const handleChange = (e) => {
    setForm((p) => ({ ...p, [e.target.name]: e.target.value }))
    setErrors((p) => ({ ...p, [e.target.name]: undefined, non_field_errors: undefined }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.new_password !== form.confirm_password) {
      setErrors({ confirm_password: 'Passwords do not match.' })
      return
    }
    setSaving(true)
    setErrors({})
    try {
      await axiosInstance.post('/auth/change-password/', {
        old_password: form.old_password,
        new_password: form.new_password,
        confirm_password: form.confirm_password,
      })
      // Clear must_change_password flag from local user state
      setUser({ ...user, must_change_password: false })
      setDone(true)
      toast('Password changed successfully.', 'success')
    } catch (err) {
      const d = err.response?.data || {}
      setErrors(d)
      toast(
        d.old_password?.[0] || d.new_password?.[0] || d.detail || 'Failed to change password.',
        'error'
      )
    } finally {
      setSaving(false)
    }
  }

  if (done) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="max-w-sm w-full text-center">
          <CardBody className="py-10 space-y-4">
            <div className="flex justify-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                <CheckCircle size={32} className="text-green-600" />
              </div>
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Password Updated</h2>
              <p className="text-sm text-gray-500 mt-1">Your new password is now active.</p>
            </div>
            <button
              onClick={() => navigate('/dashboard')}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
            >
              Go to Dashboard
            </button>
          </CardBody>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-md mx-auto space-y-5">
      {/* Required banner */}
      {mustChange && (
        <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
          <span className="w-2 h-2 rounded-full bg-amber-500 mt-1.5 animate-pulse shrink-0" />
          <div>
            <p className="text-sm font-semibold text-amber-800">Password change required</p>
            <p className="text-xs text-amber-700 mt-0.5">
              You must change your temporary password before accessing the system.
            </p>
          </div>
        </div>
      )}

      <Card>
        <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-100">
          <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center">
            <KeyRound size={18} className="text-blue-600" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-gray-900">Change Password</h1>
            <p className="text-xs text-gray-400">Choose a strong password with 12+ characters</p>
          </div>
        </div>

        <CardBody>
          <form onSubmit={handleSubmit} className="space-y-4">
            {errors.non_field_errors && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {errors.non_field_errors[0]}
              </p>
            )}

            <PasswordField
              label="Current Password"
              name="old_password"
              value={form.old_password}
              onChange={handleChange}
              error={errors.old_password?.[0]}
              show={show.old}
              onToggle={() => setShow((p) => ({ ...p, old: !p.old }))}
            />
            <PasswordField
              label="New Password"
              name="new_password"
              value={form.new_password}
              onChange={handleChange}
              error={errors.new_password?.[0]}
              show={show.new}
              onToggle={() => setShow((p) => ({ ...p, new: !p.new }))}
            />
            <PasswordField
              label="Confirm New Password"
              name="confirm_password"
              value={form.confirm_password}
              onChange={handleChange}
              error={errors.confirm_password}
              show={show.confirm}
              onToggle={() => setShow((p) => ({ ...p, confirm: !p.confirm }))}
            />

            {/* Password rules */}
            <div className="bg-gray-50 rounded-lg px-3 py-2.5 text-xs text-gray-500 space-y-1">
              <p className="font-medium text-gray-600">Password must have:</p>
              {[
                '12 or more characters',
                'At least one uppercase letter (A–Z)',
                'At least one lowercase letter (a–z)',
                'At least one number (0–9)',
                'At least one special character (!@#$%…)',
              ].map((rule) => (
                <p key={rule} className="flex items-center gap-1.5">
                  <span className="w-1 h-1 rounded-full bg-gray-400 shrink-0" />
                  {rule}
                </p>
              ))}
            </div>

            <div className="flex gap-3 pt-1">
              {!mustChange && (
                <button
                  type="button"
                  onClick={() => navigate(-1)}
                  className="flex-1 py-2.5 rounded-lg border border-gray-200 hover:bg-gray-50 text-sm font-medium text-gray-700 transition-colors"
                >
                  Cancel
                </button>
              )}
              <button
                type="submit"
                disabled={saving}
                className="flex-1 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-60
                  text-white font-semibold text-sm transition-colors"
              >
                {saving ? 'Updating…' : 'Update Password'}
              </button>
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}
