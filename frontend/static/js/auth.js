// ── Token helpers ─────────────────────────────────────────────────────────────

const Auth = {
  save(tokenData) {
    localStorage.setItem('att_token', tokenData.access_token);
    localStorage.setItem('att_role', tokenData.role);
    localStorage.setItem('att_name', tokenData.name);
    localStorage.setItem('att_user_id', tokenData.user_id);
  },

  clear() {
    ['att_token', 'att_role', 'att_name', 'att_user_id'].forEach(k => localStorage.removeItem(k));
  },

  get token() { return localStorage.getItem('att_token'); },
  get role()  { return localStorage.getItem('att_role'); },
  get name()  { return localStorage.getItem('att_name'); },
  get userId(){ return localStorage.getItem('att_user_id'); },

  isLoggedIn() { return !!this.token; },

  redirectIfLoggedIn() {
    if (this.isLoggedIn()) {
      window.location.href = this.role === 'lecturer'
        ? '/dashboard/lecturer'
        : '/dashboard/student';
    }
  },

  requireAuth(expectedRole = null) {
    if (!this.isLoggedIn()) {
      window.location.href = '/login';
      return false;
    }
    if (expectedRole && this.role !== expectedRole) {
      window.location.href = '/login';
      return false;
    }
    return true;
  },

  logout() {
    this.clear();
    window.location.href = '/login';
  },

  // Authenticated fetch wrapper
  async fetch(url, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...(this.token ? { 'Authorization': `Bearer ${this.token}` } : {}),
      ...(options.headers || {}),
    };
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) { this.logout(); return null; }
    return res;
  }
};

// ── UI helpers ────────────────────────────────────────────────────────────────

function showAlert(id, message, type = 'error') {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `alert alert-${type} show`;
  el.innerHTML = `<span>${type === 'error' ? '✕' : '✓'}</span> ${message}`;
}

function hideAlert(id) {
  const el = document.getElementById(id);
  if (el) { el.className = 'alert'; el.textContent = ''; }
}

function setLoading(btnId, loading) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  if (loading) {
    btn.dataset.origText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> Please wait…';
    btn.disabled = true;
  } else {
    btn.innerHTML = btn.dataset.origText || btn.innerHTML;
    btn.disabled = false;
  }
}

async function apiPost(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return { ok: res.ok, status: res.status, data };
}
