import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// --- Auth token wiring ---
// Tokens live in localStorage so they survive a page refresh. This is a
// pragmatic default for a fast-moving app; the trade-off is that a
// successful XSS attack could read the token from local storage. For a
// stricter posture, move to httpOnly, Secure, SameSite=strict cookies
// issued by the backend and drop the Authorization-header approach here —
// that requires a small backend change (set-cookie on login) not included
// in this pass. See PRODUCTION.md.
const ACCESS_TOKEN_KEY = 'razorrecon_access_token';
const REFRESH_TOKEN_KEY = 'razorrecon_refresh_token';

export const tokenStorage = {
  getAccessToken: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefreshToken: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  setTokens: (access: string, refresh: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, access);
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshInFlight: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = tokenStorage.getRefreshToken();
  if (!refreshToken) return null;
  try {
    const { data } = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refreshToken });
    tokenStorage.setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch {
    tokenStorage.clear();
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    // On a 401, try exactly one silent refresh-and-retry before giving up —
    // avoids bouncing the user to /login for a merely-expired access token.
    if (error.response?.status === 401 && !originalRequest._retry && tokenStorage.getRefreshToken()) {
      originalRequest._retry = true;
      if (!refreshInFlight) {
        refreshInFlight = refreshAccessToken().finally(() => {
          refreshInFlight = null;
        });
      }
      const newToken = await refreshInFlight;
      if (newToken) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      }
      // Refresh failed — force a clean login.
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// --- Auth endpoints ---
export const registerUser = (email: string, password: string, full_name?: string) =>
  api.post('/auth/register', { email, password, full_name });

export const loginUser = (email: string, password: string) => {
  const form = new URLSearchParams();
  form.set('username', email);
  form.set('password', password);
  return axios.post(`${API_BASE}/auth/login`, form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
};

export const getCurrentUser = () => api.get('/auth/me');

// --- Reconciliation / dashboard endpoints ---
export const runDemo = () => api.post('/demo');
export const runReconciliation = () => api.post('/reconcile');
export const uploadFiles = (formData: FormData) => api.post('/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
export const getDashboard = () => api.get('/dashboard');
export const getTransactions = (status?: string) => api.get('/transactions', { params: { status } });
export const getTransactionDetail = (id: string) => api.get(`/transactions/${id}`);
export const getExceptions = () => api.get('/exceptions');
export const approveException = (id: string, reason?: string) => api.post(`/exceptions/${id}/approve`, { reason });
export const rejectException = (id: string, reason?: string) => api.post(`/exceptions/${id}/reject`, { reason });
export const getAuditTrail = () => api.get('/audit');
export const getEvaluation = () => api.get('/evaluation');
export const sendChatMessage = (message: string) => api.post('/chat', { message });
