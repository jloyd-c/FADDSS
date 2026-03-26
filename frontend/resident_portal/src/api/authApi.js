import axiosInstance from './axiosInstance'

export const login = (email, password) =>
  axiosInstance.post('/auth/login/', { email, password })

export const logout = (refresh) =>
  axiosInstance.post('/auth/logout/', { refresh })

export const refreshToken = (refresh) =>
  axiosInstance.post('/auth/refresh/', { refresh })

export const getMe = () =>
  axiosInstance.get('/auth/me/')
