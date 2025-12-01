import { toast } from "sonner";
import { getUserInfo } from "@/api/system";
import { VALUECELL_BACKEND_URL } from "@/constants/api";
import { useSystemStore } from "@/store/system-store";
import type { SystemInfo } from "@/types/system";

// Backend URL cache for Tauri app
let cachedBackendUrl: string | null = null;

/**
 * Initialize backend URL from Tauri (call this on app startup)
 */
export async function initBackendUrl(): Promise<void> {
  // Only in Tauri environment
  if (typeof window !== "undefined" && "__TAURI__" in window) {
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      const url = await invoke<string | null>("get_backend_url");
      if (url) {
        cachedBackendUrl = url;
        console.log("[API] Backend URL from Tauri:", cachedBackendUrl);
      }
    } catch (e) {
      console.warn("[API] Failed to get backend URL from Tauri:", e);
    }
  }
}

/**
 * Get the backend base URL
 */
export function getBackendBaseUrl(): string {
  // 1. Check cached URL from Tauri
  if (cachedBackendUrl) {
    return cachedBackendUrl;
  }

  // 2. Check environment variable
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }

  // 3. Default fallback for development
  return "http://localhost:8000";
}

// API error type
export class ApiError extends Error {
  public status: number;
  public details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export interface ApiResponse<T> {
  code: number;
  data: T;
  msg: string;
}

// request config interface
export interface RequestConfig {
  requiresAuth?: boolean;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

export const getServerUrl = (endpoint: string) => {
  if (endpoint.startsWith("http")) return endpoint;

  const baseUrl = getBackendBaseUrl();
  const apiBase = `${baseUrl}/api/v1`;
  return `${apiBase}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
};

class ApiClient {
  // default config
  private config: RequestConfig = {
    requiresAuth: false,
    headers: {
      "Content-Type": "application/json",
    },
  };

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message =
        errorData.message ||
        errorData.detail ||
        response.statusText ||
        `HTTP ${response.status}`;

      //TODO: Handle 401 unauthorized
      if (response.status === 401) {
        try {
          const {
            data: { access_token, refresh_token },
          } = await apiClient.post<
            ApiResponse<Pick<SystemInfo, "access_token" | "refresh_token">>
          >(`${VALUECELL_BACKEND_URL}/refresh`, {
            refreshToken: useSystemStore.getState().refresh_token,
          });

          if (access_token && refresh_token) {
            const userInfo = await getUserInfo(access_token);

            if (userInfo) {
              useSystemStore.getState().setSystemInfo({
                access_token,
                refresh_token,
                ...userInfo,
              });
            }
          }
        } catch (error) {
          toast.error(JSON.stringify(error));
          useSystemStore.getState().clearSystemInfo();
        }
      } else {
        toast.error(message);
      }

      throw new ApiError(message, response.status, errorData);
    }

    const contentType = response.headers.get("content-type");
    if (contentType?.includes("application/json")) {
      return response.json();
    }

    return response.text() as unknown as T;
  }

  private async request<T>(
    method: string,
    endpoint: string,
    data?: unknown,
    config: RequestConfig = {},
  ): Promise<T> {
    const mergedConfig = { ...this.config, ...config };
    const url = getServerUrl(endpoint);

    // add authentication header
    if (mergedConfig.requiresAuth) {
      const token = useSystemStore.getState().access_token;
      if (token) {
        mergedConfig.headers!.Authorization = `Bearer ${token}`;
      }
    }

    // prepare request config
    const requestConfig: RequestInit = {
      method,
      headers: mergedConfig.headers,
      signal: mergedConfig.signal,
    };

    // add request body
    if (data && ["POST", "PUT", "PATCH"].includes(method)) {
      if (data instanceof FormData) {
        delete mergedConfig.headers!["Content-Type"];
        requestConfig.body = data;
      } else {
        requestConfig.body = JSON.stringify(data);
      }
    }

    const response = await fetch(url, requestConfig);
    return this.handleResponse<T>(response);
  }

  async get<T>(endpoint: string, config?: RequestConfig): Promise<T> {
    return this.request<T>("GET", endpoint, undefined, config);
  }

  async post<T>(
    endpoint: string,
    data?: unknown,
    config?: RequestConfig,
  ): Promise<T> {
    return this.request<T>("POST", endpoint, data, config);
  }

  async put<T>(
    endpoint: string,
    data?: unknown,
    config?: RequestConfig,
  ): Promise<T> {
    return this.request<T>("PUT", endpoint, data, config);
  }

  async patch<T>(
    endpoint: string,
    data?: unknown,
    config?: RequestConfig,
  ): Promise<T> {
    return this.request<T>("PATCH", endpoint, data, config);
  }

  async delete<T>(endpoint: string, config?: RequestConfig): Promise<T> {
    return this.request<T>("DELETE", endpoint, undefined, config);
  }

  // file upload
  async upload<T>(
    endpoint: string,
    formData: FormData,
    config?: RequestConfig,
  ): Promise<T> {
    return this.request<T>("POST", endpoint, formData, config);
  }
}

// default api client with authentication
export const apiClient = new ApiClient();
