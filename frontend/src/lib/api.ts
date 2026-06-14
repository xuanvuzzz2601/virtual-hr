import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ---- Auth ----
export const authApi = {
  login: (email: string, password: string) =>
    api.post("/api/auth/login", { email, password }),
  me: () => api.get("/api/auth/me"),
};

// ---- Jobs ----
export const jobsApi = {
  list: (status?: string) =>
    api.get("/api/jobs", { params: status ? { status } : {} }),
  get: (id: number) => api.get(`/api/jobs/${id}`),
  create: (data: unknown) => api.post("/api/jobs", data),
  update: (id: number, data: unknown) => api.put(`/api/jobs/${id}`, data),
  delete: (id: number) => api.delete(`/api/jobs/${id}`),
  publish: (id: number) => api.post(`/api/jobs/${id}/publish`),
  archive: (id: number) => api.post(`/api/jobs/${id}/archive`),
  toggleOpen: (id: number) => api.post(`/api/jobs/${id}/toggle-open`),
};

// ---- Candidates ----
export const candidatesApi = {
  listByJob: (jdId: number, params?: Record<string, unknown>) =>
    api.get(`/api/candidates/jobs/${jdId}/candidates`, { params }),
  upload: (jdId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post(`/api/candidates/jobs/${jdId}/upload`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  get: (id: number) => api.get(`/api/candidates/${id}`),
  delete: (id: number) => api.delete(`/api/candidates/${id}`),
};

// ---- Interviews ----
export const interviewsApi = {
  create: (candidateId: number, jdId: number) =>
    api.post("/api/interviews", { candidate_id: candidateId, jd_id: jdId }),
  get: (id: number) => api.get(`/api/interviews/${id}`),
  getByCandidate: (candidateId: number) =>
    api.get(`/api/interviews/candidate/${candidateId}`),
  getConfig: (id: number) => api.post(`/api/interviews/${id}/config`),
  complete: (id: number, transcript: unknown[]) =>
    api.put(`/api/interviews/${id}/complete`, { transcript }),
  evaluate: (id: number) => api.post(`/api/interviews/${id}/evaluate`),
  getEvaluation: (id: number) => api.get(`/api/interviews/${id}/evaluation`),
  mySession: () => api.get("/api/interviews/my-session"),
};
