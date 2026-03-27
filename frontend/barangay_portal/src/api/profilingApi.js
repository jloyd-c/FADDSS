import axiosInstance from './axiosInstance'

// ── Households ────────────────────────────────────────────────────────────────

export const getHouseholds = (params) =>
  axiosInstance.get('/profiling/households/', { params })

export const getHousehold = (id) =>
  axiosInstance.get(`/profiling/households/${id}/`)

export const createHousehold = (data) =>
  axiosInstance.post('/profiling/households/', data)

export const updateHousehold = (id, data) =>
  axiosInstance.patch(`/profiling/households/${id}/`, data)

export const getHouseholdSurveys = (id, params) =>
  axiosInstance.get(`/profiling/households/${id}/surveys/`, { params })

// ── Surveys ───────────────────────────────────────────────────────────────────

export const getSurveys = (params) =>
  axiosInstance.get('/profiling/surveys/', { params })

export const getSurvey = (id) =>
  axiosInstance.get(`/profiling/surveys/${id}/`)

export const createSurvey = (data) =>
  axiosInstance.post('/profiling/surveys/', data)

export const updateSurveyData = (id, data) =>
  axiosInstance.patch(`/profiling/surveys/${id}/`, data)

export const submitSurvey = (id) =>
  axiosInstance.post(`/profiling/surveys/${id}/submit/`)

export const verifySurvey = (id) =>
  axiosInstance.post(`/profiling/surveys/${id}/verify/`)

export const requestRevision = (id, data) =>
  axiosInstance.post(`/profiling/surveys/${id}/revision/`, data)

export const compareSurveys = (surveyAId, surveyBId) =>
  axiosInstance.get(`/profiling/surveys/${surveyAId}/compare/`, {
    params: { survey_b: surveyBId },
  })

// ── Families ──────────────────────────────────────────────────────────────────

export const getFamilies = (params) =>
  axiosInstance.get('/profiling/families/', { params })

// ── Persons ───────────────────────────────────────────────────────────────────

export const getPersons = (params) =>
  axiosInstance.get('/profiling/persons/', { params })

export const getPerson = (id) =>
  axiosInstance.get(`/profiling/persons/${id}/`)

export const updatePerson = (id, data) =>
  axiosInstance.patch(`/profiling/persons/${id}/`, data)

// ── Programs Availed ──────────────────────────────────────────────────────────

export const getPrograms = (params) =>
  axiosInstance.get('/profiling/programs/', { params })

// ── Form Schemas ──────────────────────────────────────────────────────────────

export const getFormSchemas = (params) =>
  axiosInstance.get('/profiling/schemas/', { params })

export const getFormSchema = (id) =>
  axiosInstance.get(`/profiling/schemas/${id}/`)

export const createFormSchema = (data) =>
  axiosInstance.post('/profiling/schemas/', data)

export const updateFormSchema = (id, data) =>
  axiosInstance.patch(`/profiling/schemas/${id}/`, data)

export const deleteFormSchema = (id) =>
  axiosInstance.delete(`/profiling/schemas/${id}/`)

// ── Query ─────────────────────────────────────────────────────────────────────

export const getConcepts = (params) =>
  axiosInstance.get('/profiling/query/concepts/', { params })

export const getConceptValues = (params) =>
  axiosInstance.get('/profiling/query/concept-values/', { params })

export const searchByConcept = (params) =>
  axiosInstance.get('/profiling/query/search/', { params })

// ── Reports ───────────────────────────────────────────────────────────────────

export const generateReport = (data) =>
  axiosInstance.post('/profiling/reports/generate/', data, {
    responseType: 'blob',
  })
