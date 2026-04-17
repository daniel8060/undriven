/* Shared utilities for modal JS files */

async function apiFetch(url, opts = {}) {
  const resp = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (resp.status === 204) return null;
  return resp.json();
}

function modalFlash(containerId, msg, type = "success") {
  const container = document.getElementById(containerId);
  container.innerHTML = `<div class="modal-flash ${type}">${msg}</div>`;
  setTimeout(() => { container.innerHTML = ""; }, 4000);
}
