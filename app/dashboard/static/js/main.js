/* PW PCB Content Manager — Main JS */

// ── Toast notifications ───────────────────────────────────────────────────
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const div = document.createElement('div');
  div.className = `pw-toast toast-${type} mb-2`;
  div.innerHTML = `
    <div class="d-flex align-items-start gap-2">
      <span style="flex-shrink:0">${type === 'success' ? '✅' : type === 'danger' ? '❌' : 'ℹ️'}</span>
      <span>${message}</span>
    </div>`;
  container.appendChild(div);
  setTimeout(() => div.remove(), 4000);
}

// ── Sidebar toggle (mobile) ───────────────────────────────────────────────
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  if (sb) sb.classList.toggle('open');
}

// ── Collect Now ───────────────────────────────────────────────────────────
function collectNow() {
  const btn = document.getElementById('collect-now-btn');
  if (!btn) return;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Collecting…';
  fetch('/api/collect-now', { method: 'POST' })
    .then(r => r.json())
    .then(d => {
      if (d.ok) {
        showToast(`Collected ${d.collected} new update${d.collected !== 1 ? 's' : ''}!`, 'success');
        setTimeout(() => location.reload(), 1500);
      } else {
        showToast('Error: ' + (d.error || 'Unknown'), 'danger');
      }
    })
    .catch(e => showToast('Network error: ' + e, 'danger'))
    .finally(() => {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-cloud-download"></i> Collect Now';
    });
}

// ── Auto-refresh updates feed every 60s ───────────────────────────────────
let autoRefreshTimer = null;
function startAutoRefresh(intervalMs = 60000) {
  autoRefreshTimer = setInterval(() => {
    updateLastCollectedBadge();
  }, intervalMs);
}

function updateLastCollectedBadge() {
  fetch('/api/updates/feed')
    .then(r => r.json())
    .then(items => {
      if (items.length > 0) {
        const badge = document.getElementById('last-collected-badge');
        if (badge) {
          const ts = new Date(items[0].collected_at + 'Z');
          badge.innerHTML = `<i class="bi bi-clock"></i> Last: ${formatRelative(ts)}`;
        }
        const countBadge = document.getElementById('sidebar-updates-count');
        if (countBadge && items.length > 0) {
          countBadge.textContent = items.length;
        }
      }
    })
    .catch(() => {}); // silently fail
}

function formatRelative(date) {
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diff < 60)   return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

// ── Hashtag pills renderer ────────────────────────────────────────────────
function renderHashtagPills() {
  const ta = document.getElementById('hashtags-ta');
  const container = document.getElementById('hashtag-pills');
  if (!ta || !container) return;
  const tags = ta.value.split(/\s+/).filter(t => t.startsWith('#'));
  container.innerHTML = tags.map(t =>
    `<span class="badge bg-dark border border-secondary text-accent me-1">${t}</span>`
  ).join('');
}

// ── Init ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  updateLastCollectedBadge();
  startAutoRefresh();

  // Hashtag pill watcher
  const hashTA = document.getElementById('hashtags-ta');
  if (hashTA) {
    hashTA.addEventListener('input', renderHashtagPills);
    renderHashtagPills();
  }

  // Auto-dismiss alerts after 5s
  document.querySelectorAll('.alert').forEach(el => {
    setTimeout(() => el.classList.remove('show'), 5000);
  });
});
