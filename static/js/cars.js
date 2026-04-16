/* Cars CRUD — /cars page */

const FUEL_TYPES = ["gasoline", "diesel", "hybrid", "electric"];

function flash(msg, type = "success") {
  const existing = document.getElementById("flash-banner");
  if (existing) existing.remove();
  const el = document.createElement("div");
  el.id = "flash-banner";
  el.className = `flash ${type}`;
  el.textContent = msg;
  document.querySelector(".page").insertBefore(el, document.getElementById("cars-card"));
  setTimeout(() => el.remove(), 4000);
}

async function apiFetch(url, opts = {}) {
  const resp = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (resp.status === 204) return null;
  return resp.json();
}

// ── Add car ──────────────────────────────────────────────────────────────────

document.getElementById("add-car-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name      = document.getElementById("new-name").value.trim();
  const mpg       = document.getElementById("new-mpg").value.trim();
  const fuel_type = document.getElementById("new-fuel").value;

  const data = await apiFetch("/api/cars", {
    method: "POST",
    body: JSON.stringify({ name, mpg: parseFloat(mpg), fuel_type }),
  });

  if (data.error) { flash(data.error, "error"); return; }

  addRow(data);
  e.target.reset();
  flash(`"${data.name}" added.`);
});

// ── Row rendering ─────────────────────────────────────────────────────────────

function buildFuelSelect(selected) {
  return `<select class="inline-select">${FUEL_TYPES.map(f =>
    `<option value="${f}"${f === selected ? " selected" : ""}>${f}</option>`
  ).join("")}</select>`;
}

function addRow(car) {
  const tbody = document.getElementById("cars-tbody");
  const tr = document.createElement("tr");
  tr.dataset.id = car.id;
  tr.innerHTML = rowHTML(car);
  tbody.appendChild(tr);
  bindRowEvents(tr);
  updateEmptyState();
}

function rowHTML(car) {
  return `
    <td class="car-name">${esc(car.name)}</td>
    <td class="car-mpg mono">${car.mpg}</td>
    <td class="car-fuel" style="color:var(--muted);font-size:.84rem">${car.fuel_type}</td>
    <td>
      ${car.is_default
        ? `<span class="default-badge">default</span>`
        : `<button class="btn-set-default">Set default</button>`}
    </td>
    <td style="display:flex;gap:.4rem;justify-content:flex-end">
      <button class="btn-edit">Edit</button>
      <button class="btn-delete">Delete</button>
    </td>`;
}

function editRowHTML(car) {
  return `
    <td><input class="inline-input" id="edit-name" value="${esc(car.name)}"></td>
    <td><input class="inline-input inline-input--short" id="edit-mpg" type="number" step="0.1" min="0" value="${car.mpg}"></td>
    <td>${buildFuelSelect(car.fuel_type)}</td>
    <td></td>
    <td style="display:flex;gap:.4rem;justify-content:flex-end">
      <button class="btn-save">Save</button>
      <button class="btn-cancel">Cancel</button>
    </td>`;
}

function bindRowEvents(tr) {
  tr.querySelector(".btn-delete")?.addEventListener("click", () => handleDelete(tr));
  tr.querySelector(".btn-edit")?.addEventListener("click", () => handleEditStart(tr));
  tr.querySelector(".btn-set-default")?.addEventListener("click", () => handleSetDefault(tr));
  tr.querySelector(".btn-save")?.addEventListener("click", () => handleSave(tr));
  tr.querySelector(".btn-cancel")?.addEventListener("click", () => handleCancel(tr));
}

// ── Handlers ──────────────────────────────────────────────────────────────────

async function handleDelete(tr) {
  const name = tr.querySelector(".car-name")?.textContent;
  if (!confirm(`Delete "${name}"?`)) return;
  const data = await apiFetch(`/api/cars/${tr.dataset.id}`, { method: "DELETE" });
  if (data && data.error) { flash(data.error, "error"); return; }
  tr.remove();
  updateEmptyState();
  flash(`"${name}" deleted.`);
  // If deleted row was default, mark the first remaining row as default
  const firstRow = document.querySelector("#cars-tbody tr");
  if (firstRow && !firstRow.querySelector(".default-badge")) {
    const btn = firstRow.querySelector(".btn-set-default");
    if (btn) btn.click();
  }
}

function handleEditStart(tr) {
  const car = {
    id:        tr.dataset.id,
    name:      tr.querySelector(".car-name").textContent,
    mpg:       parseFloat(tr.querySelector(".car-mpg").textContent),
    fuel_type: tr.querySelector(".car-fuel").textContent.trim(),
  };
  tr.innerHTML = editRowHTML(car);
  bindRowEvents(tr);
  tr.querySelector("#edit-name").focus();
}

async function handleSave(tr) {
  const name      = tr.querySelector("#edit-name").value.trim();
  const mpg       = parseFloat(tr.querySelector("#edit-mpg").value);
  const fuel_type = tr.querySelector(".inline-select").value;

  const data = await apiFetch(`/api/cars/${tr.dataset.id}`, {
    method: "PATCH",
    body: JSON.stringify({ name, mpg, fuel_type }),
  });
  if (data.error) { flash(data.error, "error"); return; }
  tr.innerHTML = rowHTML(data);
  bindRowEvents(tr);
  flash(`"${data.name}" saved.`);
}

function handleCancel(tr) {
  // Re-fetch row state from the DOM data we saved
  const car = {
    id:        tr.dataset.id,
    name:      tr.dataset.name,
    mpg:       parseFloat(tr.dataset.mpg),
    fuel_type: tr.dataset.fuel,
    is_default: tr.dataset.isDefault === "true",
  };
  tr.innerHTML = rowHTML(car);
  bindRowEvents(tr);
}

async function handleSetDefault(tr) {
  const data = await apiFetch(`/api/cars/${tr.dataset.id}/set-default`, { method: "POST" });
  if (data.error) { flash(data.error, "error"); return; }
  // Update all rows: clear other badges, set this one
  document.querySelectorAll("#cars-tbody tr").forEach(row => {
    const badge = row.querySelector(".default-badge");
    const btn   = row.querySelector(".btn-set-default");
    if (row === tr) {
      if (btn) btn.outerHTML = `<span class="default-badge">default</span>`;
    } else {
      if (badge) badge.outerHTML = `<button class="btn-set-default">Set default</button>`;
      row.querySelector(".btn-set-default")?.addEventListener("click", () => handleSetDefault(row));
    }
  });
  flash("Default car updated.");
}

// ── Utils ─────────────────────────────────────────────────────────────────────

function esc(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function updateEmptyState() {
  const tbody = document.getElementById("cars-tbody");
  const empty = document.getElementById("cars-empty");
  if (empty) empty.style.display = tbody.children.length === 0 ? "" : "none";
}

// ── Init — bind events on server-rendered rows ────────────────────────────────

document.querySelectorAll("#cars-tbody tr").forEach(tr => {
  // Stash original values for cancel
  tr.dataset.name      = tr.querySelector(".car-name")?.textContent || "";
  tr.dataset.mpg       = tr.querySelector(".car-mpg")?.textContent || "";
  tr.dataset.fuel      = tr.querySelector(".car-fuel")?.textContent.trim() || "";
  tr.dataset.isDefault = tr.querySelector(".default-badge") ? "true" : "false";
  bindRowEvents(tr);
});
