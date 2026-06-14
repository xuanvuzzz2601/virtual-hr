export interface User {
  id: number;
  email: string;
  name: string;
  role: "admin" | "hr" | "hiring_manager" | "candidate";
  is_active: boolean;
  created_at: string;
}

export function getUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("user");
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export function setAuth(token: string, user: User) {
  localStorage.setItem("token", token);
  localStorage.setItem("user", JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
}

export function isAuthenticated(): boolean {
  return !!getToken();
}
