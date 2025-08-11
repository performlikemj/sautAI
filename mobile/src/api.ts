// Minimal typed API client targeting existing Django endpoints
export type Tokens = { access: string; refresh: string };
export type UserInfo = {
  user_id: number;
  username: string;
  email: string;
  access: string;
  refresh: string;
  is_chef?: boolean;
  current_role?: 'customer' | 'chef';
  email_confirmed?: boolean;
  timezone?: string;
  preferred_language?: string;
};

let baseUrl = '';
export function setBaseUrl(url: string) {
  baseUrl = url.replace(/\/$/, '');
}

let getTokens: () => Promise<Tokens | null> = async () => null;
let setTokens: (t: Tokens | null) => Promise<void> = async () => {};

export function wireTokenStorage(getter: typeof getTokens, setter: typeof setTokens) {
  getTokens = getter;
  setTokens = setter;
}

async function request(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const tokens = await getTokens();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string>),
  };
  if (tokens?.access) headers['Authorization'] = `Bearer ${tokens.access}`;

  console.log('[API] request', { url: `${baseUrl}${path}`, method: init.method || 'GET', body: init.body });
  const resp = await fetch(`${baseUrl}${path}`, { ...init, headers, credentials: 'include' });
  console.log('[API] response', { url: `${baseUrl}${path}`, status: resp.status });
  if (resp.status !== 401 || !tokens || !retry) return resp;

  // refresh
  const refreshResp = await fetch(`${baseUrl}/auth/api/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: tokens.refresh }),
    credentials: 'include',
  });
  if (!refreshResp.ok) return resp;
  const newTokens = (await refreshResp.json()) as Tokens;
  await setTokens({ access: newTokens.access, refresh: tokens.refresh });
  // retry original
  return request(path, init, false);
}

// Auth
export async function login(username: string, password: string): Promise<UserInfo> {
  const r = await fetch(`${baseUrl}/auth/api/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
    credentials: 'include',
  });
  if (!r.ok) throw new Error('Login failed');
  return r.json();
}

export async function userDetails(): Promise<any> {
  const r = await request('/auth/api/user_details/');
  if (!r.ok) throw new Error('Failed user_details');
  return r.json();
}

// Assistant streaming (SSE)
export async function streamAssistant({
  message,
  threadId,
  isGuest,
  onEvent,
  onError,
}: {
  message: string;
  threadId?: string | null;
  isGuest?: boolean;
  onEvent: (ev: any) => void;
  onError?: (e: any) => void;
}): Promise<() => void> {
  const tokens = await getTokens();
  const path = isGuest
    ? '/customer_dashboard/api/assistant/guest-stream-message/'
    : '/customer_dashboard/api/assistant/stream-message/';
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (!isGuest && tokens?.access) headers['Authorization'] = `Bearer ${tokens.access}`;
  const controller = new AbortController();
  const body: any = { message };
  if (threadId) body.response_id = threadId;

  try {
    const resp = await fetch(`${baseUrl}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal: controller.signal,
      credentials: 'include',
    });
    if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    (async () => {
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          let idx;
          while ((idx = buf.indexOf('\n')) >= 0) {
            const line = buf.slice(0, idx).trim();
            buf = buf.slice(idx + 1);
            if (!line.startsWith('data:')) continue;
            const payload = line.slice(5).trim();
            try {
              const json = JSON.parse(payload);
              onEvent(json);
            } catch {}
          }
        }
      } catch (e) {
        onError?.(e);
      }
    })();
  } catch (e) {
    onError?.(e);
  }

  return () => controller.abort();
}

// Threads
export async function threadHistory(page = 1) {
  const r = await request(`/customer_dashboard/api/thread_history/?page=${page}`);
  if (!r.ok) throw new Error('Failed thread_history');
  return r.json();
}

export async function threadDetail(id: string) {
  const r = await request(`/customer_dashboard/api/thread_detail/${id}/`);
  if (!r.ok) throw new Error('Failed thread_detail');
  return r.json();
}

// Pantry
export async function getPantry(page = 1) {
  const r = await request(`/meals/api/pantry-items/?page=${page}`);
  if (!r.ok) throw new Error('Failed pantry');
  return r.json();
}

export async function createPantryItem(data: any) {
  const r = await request(`/meals/api/pantry-items/`, { method: 'POST', body: JSON.stringify(data) });
  if (!r.ok) throw new Error('Failed create pantry');
  return r.json();
}

export async function updatePantryItem(id: number, data: any) {
  const r = await request(`/meals/api/pantry-items/${id}/`, { method: 'PUT', body: JSON.stringify(data) });
  if (!r.ok) throw new Error('Failed update pantry');
  return r.json();
}

export async function deletePantryItem(id: number) {
  const r = await request(`/meals/api/pantry-items/${id}/`, { method: 'DELETE' });
  if (r.status !== 204) throw new Error('Failed delete pantry');
}

// Chef meals
export async function chefMealsByPostal(params: Record<string, any>) {
  const qs = new URLSearchParams(params as any).toString();
  const r = await request(`/meals/api/chef-meals-by-postal-code/?${qs}`);
  if (!r.ok) throw new Error('Failed chef meals');
  return r.json();
}

// Profile/goals/health metrics
export async function updateProfile(data: any) {
  const r = await request(`/auth/api/update_profile/`, { method: 'POST', body: JSON.stringify(data) });
  if (!r.ok) throw new Error('Failed update profile');
  return r.json();
}

// Meal plans
export async function getMealPlans(params: { week_start_date?: string }) {
  const qs = new URLSearchParams(params as any).toString();
  const r = await request(`/meals/api/meal_plans/?${qs}`);
  if (!r.ok) throw new Error('Failed meal plans');
  return r.json();
}

export async function approveMealPlan(meal_plan_id: number) {
  const r = await request(`/meals/api/approve_meal_plan/`, {
    method: 'POST',
    body: JSON.stringify({ meal_plan_id }),
  });
  if (!r.ok) throw new Error('Failed approve plan');
  return r.json();
}

export async function removeMealFromPlan(meal_plan_meal_id: number) {
  const r = await request(`/meals/api/remove_meal_from_plan/`, {
    method: 'POST',
    body: JSON.stringify({ meal_plan_meal_id }),
  });
  if (!r.ok) throw new Error('Failed remove meal');
  return r.json();
}

export async function updateMealsWithPrompt(meal_plan_id: number, prompt: string) {
  const r = await request(`/meals/api/update_meals_with_prompt/`, {
    method: 'POST',
    body: JSON.stringify({ meal_plan_id, prompt }),
  });
  if (!r.ok) throw new Error('Failed update meals');
  return r.json();
}

export async function replaceMealPlanMeal(payload: {
  meal_plan_meal_id: number;
  chef_meal_id: number;
  event_id?: number | null;
  quantity?: number;
  special_requests?: string;
}) {
  const r = await request(`/meals/api/replace_meal_plan_meal/`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error('Failed replace meal');
  return r.json();
}

export async function generateCookingInstructions(meal_plan_meal_ids: number[]) {
  const r = await request(`/meals/api/generate_cooking_instructions/`, {
    method: 'POST',
    body: JSON.stringify({ meal_plan_meal_ids }),
  });
  if (!r.ok) throw new Error('Failed generate instructions');
  return r.json();
}

export async function fetchInstructions(meal_plan_meal_ids: number[]) {
  const qs = new URLSearchParams({ meal_plan_meal_ids: meal_plan_meal_ids.join(',') }).toString();
  const r = await request(`/meals/api/fetch_instructions/?${qs}`);
  if (!r.ok) throw new Error('Failed fetch instructions');
  return r.json();
}

export async function emailApprovedMealPlan(meal_plan_id: number, email: string) {
  const r = await request(`/meals/api/email_approved_meal_plan/`, {
    method: 'POST',
    body: JSON.stringify({ meal_plan_id, email }),
  });
  if (!r.ok) throw new Error('Failed email plan');
  return r.json();
}

export async function generateEmergencySupply(days: number) {
  const r = await request(`/meals/api/generate_emergency_supply/`, {
    method: 'POST',
    body: JSON.stringify({ days }),
  });
  if (!r.ok) throw new Error('Failed emergency supply');
  return r.json();
}

export async function generateInstacartLink(meal_plan_id: number) {
  const r = await request(`/meals/api/generate-instacart-link/`, {
    method: 'POST',
    body: JSON.stringify({ meal_plan_id }),
  });
  if (!r.ok) throw new Error('Failed generate instacart link');
  return r.json();
}

export async function mealPlanInstacartUrl(meal_plan_id: number) {
  const r = await request(`/meals/api/meal-plans/${meal_plan_id}/instacart-url/`);
  if (!r.ok) throw new Error('Failed get instacart url');
  return r.json();
}

// Health metrics
export async function getHealthMetrics(user_id: number) {
  const qs = new URLSearchParams({ user_id: String(user_id) }).toString();
  const r = await request(`/customer_dashboard/api/health_metrics/?${qs}`);
  if (!r.ok) throw new Error('Failed health metrics');
  return r.json();
}

export async function saveHealthMetrics(payload: {
  id: number; // user id
  date_recorded: string; // YYYY-MM-DD
  weight?: number | null;
  mood?: string;
  energy_level?: number;
}) {
  const r = await request(`/customer_dashboard/api/health_metrics/`, { method: 'POST', body: JSON.stringify(payload) });
  if (!r.ok) throw new Error('Failed save metrics');
  return r.json();
}

// Daily summary stream
export async function streamUserSummary({
  date,
  onEvent,
  onError,
}: {
  date?: string;
  onEvent: (data: any) => void;
  onError?: (e: any) => void;
}) {
  const tokens = await getTokens();
  const qs = new URLSearchParams(date ? { date } : {}).toString();
  const url = `/customer_dashboard/api/stream_user_summary/${qs ? `?${qs}` : ''}`;
  const headers: Record<string, string> = {};
  if (tokens?.access) headers['Authorization'] = `Bearer ${tokens.access}`;
  const controller = new AbortController();
  try {
    const resp = await fetch(`${baseUrl}${url}`, { headers, signal: controller.signal, credentials: 'include' });
    if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    (async () => {
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          let idx;
          while ((idx = buf.indexOf('\n')) >= 0) {
            const line = buf.slice(0, idx).trim();
            buf = buf.slice(idx + 1);
            if (!line.startsWith('data:')) continue;
            const payload = line.slice(5).trim();
            try {
              const json = JSON.parse(payload);
              onEvent(json);
            } catch {}
          }
        }
      } catch (e) {
        onError?.(e);
      }
    })();
  } catch (e) {
    onError?.(e);
  }
  return () => controller.abort();
}

// Chef
export async function chefDashboardStats() {
  const r = await request(`/meals/api/chef-dashboard-stats/`);
  if (!r.ok) throw new Error('Failed chef dashboard stats');
  return r.json();
}

// Meal plan detail
export async function getMealPlan(id: number) {
  const r = await request(`/meals/api/meal_plans/${id}/`);
  if (!r.ok) throw new Error('Failed meal plan detail');
  return r.json();
}


