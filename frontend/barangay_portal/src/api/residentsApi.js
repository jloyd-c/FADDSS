import axiosInstance from './axiosInstance'

// ── Puroks ───────────────────────────────────────────────────────────────────
export const getPuroks = (params) =>
  axiosInstance.get('/residents/puroks/', { params })

export const createPurok = (data) =>
  axiosInstance.post('/residents/puroks/', data)

export const updatePurok = (id, data) =>
  axiosInstance.patch(`/residents/puroks/${id}/`, data)

export const deletePurok = (id) =>
  axiosInstance.delete(`/residents/puroks/${id}/`)

// ── Residents ────────────────────────────────────────────────────────────────
export const getResidents = (params) =>
  axiosInstance.get('/residents/residents/', { params })

export const getResident = (id) =>
  axiosInstance.get(`/residents/residents/${id}/`)

export const createResident = (data) =>
  axiosInstance.post('/residents/residents/', data)

export const updateResident = (id, data) =>
  axiosInstance.patch(`/residents/residents/${id}/`, data)

export const deleteResident = (id) =>
  axiosInstance.delete(`/residents/residents/${id}/`)

export const createResidentAccount = (id, data = {}) =>
  axiosInstance.post(`/residents/residents/${id}/create-account/`, data)

export const getSuggestedUsername = (id) =>
  axiosInstance.get(`/residents/residents/${id}/suggested-username/`)
