import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || '';
    if (error.response?.status === 401 && url !== '/auth/me' && url !== '/auth/login') {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// --- Scheduler API helpers ---
export interface ScheduleData {
  schedule: string;
}

export interface ScheduleResponse {
  workflow_id: number;
  schedule: string;
  next_run_at: string;
  is_active: boolean;
}

export async function getSchedule(workflowId: number) {
  return api.get<ScheduleResponse>(`/workflows/${workflowId}/schedule`);
}

export async function setSchedule(workflowId: number, schedule: string) {
  return api.post<ScheduleResponse>(`/workflows/${workflowId}/schedule`, { schedule });
}

export async function deleteSchedule(workflowId: number) {
  return api.delete(`/workflows/${workflowId}/schedule`);
}

// --- Webhook API helpers ---
export interface WebhookCreatePayload {
  secret?: string;
}

export interface WebhookResponse {
  workflow_id: number;
  webhook_key: string;
  webhook_url: string;
  is_active: boolean;
}

export interface WebhookCreateResponse {
  workflow_id: number;
  webhook_key: string;
  webhook_url: string;
  webhook_secret: string;
  is_active: boolean;
}

export async function createWebhook(workflowId: number, payload: WebhookCreatePayload = {}) {
  return api.post<WebhookCreateResponse>(`/workflows/${workflowId}/webhooks`, payload);
}

export async function listWebhooks(workflowId: number) {
  return api.get<WebhookResponse[]>(`/workflows/${workflowId}/webhooks`);
}

export async function deleteWebhook(webhookKey: string) {
  return api.delete(`/webhooks/${webhookKey}`);
}

// --- Execution Node API helpers ---
export interface ExecutionNode {
  id: number;
  execution_id: number;
  node_ref: string;
  node_type: string;
  status: 'completed' | 'failed' | 'skipped' | 'pending' | 'running';
  input_data: Record<string, any> | null;
  output_data: Record<string, any> | null;
  error_log: string | null;
  duration_ms: number | null;
  started_at: string;
  completed_at: string | null;
}

export async function fetchExecutionNodes(executionId: number): Promise<ExecutionNode[]> {
  const res = await api.get<ExecutionNode[]>(`/workflows/executions/${executionId}/nodes`);
  return res.data;
}
