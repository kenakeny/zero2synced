// API client for the Zero-to-Synced backend.
//
// Note: /chat and /files are POST endpoints that return Server-Sent Events.
// The browser's native EventSource only does GET (and can't send an auth
// header), so we stream the response body with fetch() and parse SSE by hand.

const BASE = import.meta.env.VITE_API_BASE || "";
const TOKEN_KEY = "z2s_token";

// --- token storage ---------------------------------------------------------
export const token = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

let onUnauthorized = () => {};
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

function authHeaders(extra = {}) {
  const t = token.get();
  return t ? { ...extra, Authorization: `Bearer ${t}` } : extra;
}

async function handleResponse(res) {
  if (res.status === 401) {
    token.clear();
    onUnauthorized();
    throw new Error("Your session expired. Please sign in again.");
  }
  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.json()).detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json();
}

// --- auth ------------------------------------------------------------------
export const auth = {
  signup: (email, password) =>
    fetch(`${BASE}/api/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }).then(handleResponse),

  login: (email, password) =>
    fetch(`${BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }).then(handleResponse),

  me: () =>
    fetch(`${BASE}/api/auth/me`, { headers: authHeaders() }).then(handleResponse),
};

// --- fivetran connection ---------------------------------------------------
export const fivetran = {
  status: () =>
    fetch(`${BASE}/api/fivetran/status`, { headers: authHeaders() }).then(handleResponse),

  connect: (api_key, api_secret) =>
    fetch(`${BASE}/api/fivetran/connect`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ api_key, api_secret }),
    }).then(handleResponse),

  disconnect: () =>
    fetch(`${BASE}/api/fivetran/disconnect`, {
      method: "DELETE",
      headers: authHeaders(),
    }).then(handleResponse),
};

// --- sessions / history / files -------------------------------------------
export const api = {
  createSession: () =>
    fetch(`${BASE}/api/sessions`, {
      method: "POST",
      headers: authHeaders(),
    }).then(handleResponse),

  listSessions: () =>
    fetch(`${BASE}/api/sessions`, { headers: authHeaders() }).then(handleResponse),

  history: (sid) =>
    fetch(`${BASE}/api/sessions/${sid}/history`, { headers: authHeaders() }).then(
      handleResponse
    ),

  listFiles: (sid) =>
    fetch(`${BASE}/api/sessions/${sid}/files`, { headers: authHeaders() }).then(
      handleResponse
    ),
};

// --- SSE over fetch --------------------------------------------------------
function parseFrame(raw) {
  let event = "message";
  const dataLines = [];
  for (const line of raw.split("\n")) {
    if (line.startsWith(":")) continue; // comment / keep-alive ping
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).replace(/^ /, ""));
  }
  if (dataLines.length === 0) return null;
  let data = dataLines.join("\n");
  try {
    data = JSON.parse(data);
  } catch {
    /* leave as string */
  }
  return { event, data };
}

async function streamPost(url, { body, isForm, onEvent, signal }) {
  const headers = authHeaders(isForm ? {} : { "Content-Type": "application/json" });
  const res = await fetch(url, {
    method: "POST",
    headers,
    body: isForm ? body : JSON.stringify(body),
    signal,
  });

  if (res.status === 401) {
    token.clear();
    onUnauthorized();
    throw new Error("Your session expired. Please sign in again.");
  }
  if (!res.ok || !res.body) {
    let detail = "";
    try {
      detail = (await res.json()).detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let m;
    while ((m = buffer.match(/\r?\n\r?\n/))) {
      const idx = m.index;
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + m[0].length);
      const frame = parseFrame(raw);
      if (frame) onEvent(frame);
    }
  }
}

export function sendMessage(sid, message, { onEvent, signal }) {
  return streamPost(`${BASE}/api/sessions/${sid}/chat`, {
    body: { message },
    onEvent,
    signal,
  });
}

export function uploadFile(sid, file, { onEvent, signal }) {
  const form = new FormData();
  form.append("file", file);
  return streamPost(`${BASE}/api/sessions/${sid}/files`, {
    body: form,
    isForm: true,
    onEvent,
    signal,
  });
}
