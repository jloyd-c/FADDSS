import axiosInstance from './axiosInstance'

// ── Admins ───────────────────────────────────────────────────────────────────
export const getAdmins = (params) =>
  axiosInstance.get('/users/admins/', { params })

export const getAdmin = (id) =>
  axiosInstance.get(`/users/admins/${id}/`)

export const createAdmin = (data) =>
  axiosInstance.post('/users/admins/', data)

export const updateAdmin = (id, data) =>
  axiosInstance.patch(`/users/admins/${id}/`, data)

export const deleteAdmin = (id) =>
  axiosInstance.delete(`/users/admins/${id}/`)

// ── Staff ────────────────────────────────────────────────────────────────────
export const getStaff = (params) =>
  axiosInstance.get('/users/staff/', { params })

export const getStaffMember = (id) =>
  axiosInstance.get(`/users/staff/${id}/`)

export const createStaff = (data) =>
  axiosInstance.post('/users/staff/', data)

export const updateStaff = (id, data) =>
  axiosInstance.patch(`/users/staff/${id}/`, data)

export const deleteStaff = (id) =>
  axiosInstance.delete(`/users/staff/${id}/`)
