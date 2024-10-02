import { dev } from "$app/environment";

export function apiRoot(): string {
  if (dev) {
    // Development environment (localhost)
    return "http://localhost:8000/api";
  }
  
  // Production environment (use an environment variable or hardcoded URL)
  return import.meta.env.VITE_API_BASE_URL
}
