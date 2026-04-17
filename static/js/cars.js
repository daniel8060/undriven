/* Cars modal — included on index and trips pages */

const FUEL_TYPES = ["gasoline", "diesel", "hybrid", "electric"];

// ── Modal open / close ────────────────────────────────────────────────────────

const backdrop = document.getElementById("carsModalBackdrop");

function openCarsModal() {
  backdrop.classList.add("open");
  document.body.style.overflow = "hidden";
}

function closeCarsModal() {
  backdrop.classList.remove("open");
  document.body.style.overflow = "";
}

document.getElementById("carsModalClose").addEventListener("click", closeCarsModal);
backdrop.addEventListener("click", (e) => { if (e.target === backdrop) closeCarsModal(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeCarsModal(); });

const flash = (msg, type = "success") => modalFlash("cars-modal-flash", msg, type);

// ── Add car ───────────────────────────────────────────────────────────────────

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
  syncCarDropdown();
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
  stashData(tr, car);
  tbody.appendChild(tr);
  bindRowEvents(tr);
  updateEmptyState();
}

function rowHTML(car) {
  return `
    <td class="drag-handle" title="Drag to reorder">⠿</td>
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
    <td class="drag-handle" title="Drag to reorder">⠿</td>
    <td><input class="inline-input" id="edit-name" value="${esc(car.name)}"></td>
    <td><input class="inline-input inline-input--short" id="edit-mpg" type="number" step="0.1" min="0" value="${car.mpg}"></td>
    <td>${buildFuelSelect(car.fuel_type)}</td>
    <td></td>
    <td style="display:flex;gap:.4rem;justify-content:flex-end">
      <button class="btn-save">Save</button>
      <button class="btn-cancel">Cancel</button>
    </td>`;
}

function stashData(tr, car) {
  tr.dataset.name      = car.name ?? tr.querySelector(".car-name")?.textContent ?? "";
  tr.dataset.mpg       = car.mpg  ?? tr.querySelector(".car-mpg")?.textContent  ?? "";
  tr.dataset.fuel      = car.fuel_type ?? tr.querySelector(".car-fuel")?.textContent?.trim() ?? "";
  tr.dataset.isDefault = (car.is_default ?? tr.querySelector(".default-badge") !== null).toString();
}

function bindRowEvents(tr) {
  tr.querySelector(".btn-delete")?.addEventListener("click", () => handleDelete(tr));
  tr.querySelector(".btn-edit")?.addEventListener("click",   () => handleEditStart(tr));
  tr.querySelector(".btn-set-default")?.addEventListener("click", () => handleSetDefault(tr));
  tr.querySelector(".btn-save")?.addEventListener("click",   () => handleSave(tr));
  tr.querySelector(".btn-cancel")?.addEventListener("click", () => handleCancel(tr));
  bindDragEvents(tr);
}

// ── CRUD handlers ─────────────────────────────────────────────────────────────

async function handleDelete(tr) {
  const name = tr.querySelector(".car-name")?.textContent;
  if (!confirm(`Delete "${name}"?`)) return;
  const data = await apiFetch(`/api/cars/${tr.dataset.id}`, { method: "DELETE" });
  if (data?.error) { flash(data.error, "error"); return; }
  tr.remove();
  updateEmptyState();
  flash(`"${name}" deleted.`);
  syncCarDropdown();
  const firstRow = document.querySelector("#cars-tbody tr");
  if (firstRow && !firstRow.querySelector(".default-badge")) {
    firstRow.querySelector(".btn-set-default")?.click();
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
  stashData(tr, data);
  bindRowEvents(tr);
  flash(`"${data.name}" saved.`);
  syncCarDropdown();
}

function handleCancel(tr) {
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
  if (data?.error) { flash(data.error, "error"); return; }
  document.querySelectorAll("#cars-tbody tr").forEach(row => {
    if (row === tr) {
      row.querySelector(".btn-set-default")?.outerHTML;
      const btn = row.querySelector(".btn-set-default");
      if (btn) btn.outerHTML = `<span class="default-badge">default</span>`;
      row.dataset.isDefault = "true";
    } else {
      const badge = row.querySelector(".default-badge");
      if (badge) {
        badge.outerHTML = `<button class="btn-set-default">Set default</button>`;
        row.querySelector(".btn-set-default").addEventListener("click", () => handleSetDefault(row));
      }
      row.dataset.isDefault = "false";
    }
  });
  flash("Default car updated.");
  syncCarDropdown();
}

// ── Drag-to-reorder ───────────────────────────────────────────────────────────

let dragSrc = null;

function bindDragEvents(tr) {
  const handle = tr.querySelector(".drag-handle");
  if (!handle) return;

  handle.addEventListener("mousedown", () => { tr.draggable = true; });
  handle.addEventListener("mouseup",   () => { tr.draggable = false; });

  tr.addEventListener("dragstart", (e) => {
    dragSrc = tr;
    e.dataTransfer.effectAllowed = "move";
    setTimeout(() => tr.classList.add("dragging"), 0);
  });

  tr.addEventListener("dragend", () => {
    tr.draggable = false;
    tr.classList.remove("dragging");
    document.querySelectorAll("#cars-tbody tr").forEach(r => r.classList.remove("drag-over"));
    persistOrder();
  });

  tr.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (dragSrc && dragSrc !== tr) {
      document.querySelectorAll("#cars-tbody tr").forEach(r => r.classList.remove("drag-over"));
      tr.classList.add("drag-over");
    }
  });

  tr.addEventListener("drop", (e) => {
    e.preventDefault();
    if (!dragSrc || dragSrc === tr) return;
    const tbody = tr.closest("tbody");
    const rows  = [...tbody.querySelectorAll("tr")];
    const srcIdx = rows.indexOf(dragSrc);
    const tgtIdx = rows.indexOf(tr);
    if (srcIdx < tgtIdx) tbody.insertBefore(dragSrc, tr.nextSibling);
    else                  tbody.insertBefore(dragSrc, tr);
    tr.classList.remove("drag-over");
  });
}

async function persistOrder() {
  const ids = [...document.querySelectorAll("#cars-tbody tr")].map(tr => parseInt(tr.dataset.id));
  await apiFetch("/api/cars/reorder", { method: "POST", body: JSON.stringify({ ids }) });
  syncCarDropdown();
}

// ── Sync the log-form car dropdown (if present on this page) ──────────────────

function syncCarDropdown() {
  const select = document.getElementById("f-car");
  if (!select) return;

  const currentVal = select.value;
  // Clear all options except "— none —"
  while (select.options.length > 1) select.remove(1);

  document.querySelectorAll("#cars-tbody tr").forEach(tr => {
    const name = tr.querySelector(".car-name")?.textContent;
    if (!name) return;
    const opt = new Option(name, name);
    const isDefault = tr.querySelector(".default-badge") !== null;
    if (isDefault && !currentVal) opt.selected = true;
    else if (name === currentVal) opt.selected = true;
    select.add(opt);
  });
}

// ── Utils ─────────────────────────────────────────────────────────────────────

function esc(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function updateEmptyState() {
  const empty = document.getElementById("cars-empty");
  const tbody = document.getElementById("cars-tbody");
  if (empty) empty.style.display = tbody.children.length === 0 ? "" : "none";
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.querySelectorAll("#cars-tbody tr").forEach(tr => {
  stashData(tr, {});
  bindRowEvents(tr);
});
