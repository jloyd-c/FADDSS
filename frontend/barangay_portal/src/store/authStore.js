import { create } from 'zustand'
import { login as loginApi, logout as logoutApi } from '../api/authApi'

const useAuthStore = create((set, get) => ({
  user: null,
  accessToken: localStorage.getItem('access_token') || null,
  refreshToken: localStorage.getItem('refresh_token') || null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null })
    try {
      const { data } = await loginApi(email, password)
      localStorage.setItem('access_token', data.access)
      localStorage.setItem('refresh_token', data.refresh)
      set({
        user: data.user,
        accessToken: data.access,
        refreshToken: data.refresh,
        isAuthenticated: true,
        isLoading: false,
      })
      return data
    } catch (error) {
      const message = error.response?.data?.non_field_errors?.[0]
        || error.response?.data?.detail
        || 'Login failed.'
      set({ error: message, isLoading: false })
      throw error
    }
  },

  logout: async () => {
    try {
      const refresh = get().refreshToken
      if (refresh) await logoutApi(refresh)
    } catch (_) {
      // Ignore errors on logout — clear state regardless
    } finally {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
    }
  },

  setUser: (user) => set({ user }),
  clearError: () => set({ error: null }),
}))

export default useAuthStore
