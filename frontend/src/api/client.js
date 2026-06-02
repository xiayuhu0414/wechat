const API_BASE = import.meta.env.VITE_API_BASE || ''

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {})
  const token = localStorage.getItem('autowechat_token')
  if (token) headers.set('x-autowechat-token', token)
  if (!(options.body instanceof FormData) && options.body !== undefined) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    body: options.body instanceof FormData ? options.body : options.body ? JSON.stringify(options.body) : undefined,
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `HTTP ${response.status}`)
  }
  return response.json()
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body }),
  patch: (path, body) => request(path, { method: 'PATCH', body }),
  put: (path, body) => request(path, { method: 'PUT', body }),
  delete: (path) => request(path, { method: 'DELETE' }),
  upload: (path, formData) => request(path, { method: 'POST', body: formData }),
}

export function taskSocketUrl() {
  const token = localStorage.getItem('autowechat_token')
  const base = API_BASE || window.location.origin
  const url = new URL('/ws/tasks/logs', base)
  url.protocol = url.protocol.replace('http', 'ws')
  if (token) url.searchParams.set('token', token)
  return url.toString()
}
