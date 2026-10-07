import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'
export const api = axios.create({ baseURL: API_URL })
export const getToken = () => localStorage.getItem('eventsphere_access_token')
export const setToken = (token) => localStorage.setItem('eventsphere_access_token', token)
export const clearToken = () => localStorage.removeItem('eventsphere_access_token')
api.interceptors.request.use((config) => { const token = getToken(); if (token) config.headers.Authorization = `Bearer ${token}`; return config })
api.interceptors.response.use((response) => response, (error) => { if (error.response?.status === 401) { clearToken(); window.dispatchEvent(new Event('eventsphere:unauthorized')) } return Promise.reject(error) })
