/* Addresses modal + chip quick-fill for log form */

// ── Modal open / close ────────────────────────────────────────────────────────

const addrBackdrop = document.getElementById("addrModalBackdrop");

function openAddressesModal() {
  addrBackdrop.classList.add("open");
  document.body.style.overflow = "hidden";
}

function closeAddressesModal() {
  addrBackdrop.classList.remove("open");
  document.body.style.overflow = "";
}

document.getElementById("addrModalClose").addEventListener("click", closeAddressesModal);
addrBackdrop.addEventListener("click", (e) => { if (e.target === addrBackdrop) closeAddressesModal(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeAddressesModal(); });

// ── Flash ─────────────────────────────────────────────────────────────────────

function addrFlash(msg, type = "success") {
  const container = document.getElementById("addr-modal-flash");
  container.innerHTML = `<div class="modal-flash ${type}">${msg}</div>`;
  setTimeout(() => { container.innerHTML = ""; }, 4000);
}

// ── API helper ────────────────────────────────────────────────────────────────

async function addrFetch(url, opts = {}) {
  const resp = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (resp.status === 204) return null;
  return resp.json();
}

// ── Chips (log form quick-fill) ───────────────────────────────────────────────

let chipTarget = "start"; // which input chips fill next

const fStart = document.getElementById("f-start");
const fEnd   = document.getElementById("f-end");

if (fStart) {
  fStart.addEventListener("focus", () => { chipTarget = "start"; });
  fStart.addEventListener("input", () => {
    document.querySelectorAll(".addr-chip.chip-from").forEach(c => c.classList.remove("chip-from"));
  });
}
if (fEnd) {
  fEnd.addEventListener("focus", () => { chipTarget = "end"; });
  fEnd.addEventListener("input", () => {
    document.querySelectorAll(".addr-chip.chip-to").forEach(c => c.classList.remove("chip-to"));
  });
}

function renderChips(addresses) {
  const container = document.getElementById("addr-chips");
  if (!container) return;
  container.innerHTML = "";
  addresses.forEach(addr => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "addr-chip";
    chip.dataset.id      = addr.id;
    chip.dataset.address = addr.address;

    // Build label + optional badge
    chip.innerHTML = addrEsc(addr.label);

    // Restore visual state if inputs already have this address
    if (fStart && fStart.value === addr.address) chip.classList.add("chip-from");
    if (fEnd   && fEnd.value   === addr.address) chip.classList.add("chip-to");

    chip.addEventListener("click", () => handleChipClick(chip));
    container.appendChild(chip);
  });
}

function handleChipClick(chip) {
  const address = chip.dataset.address;

  if (chip.classList.contains("chip-from")) {
    // Un-assign From
    chip.classList.remove("chip-from");
    if (fStart) fStart.value = "";
    chipTarget = "start";
    return;
  }

  if (chip.classList.contains("chip-to")) {
    // Un-assign To
    chip.classList.remove("chip-to");
    if (fEnd) fEnd.value = "";
    chipTarget = "end";
    return;
  }

  // Assign to chipTarget field
  if (chipTarget === "start") {
    // Mutual exclusion: if same address is already in To, don't allow
    if (fEnd && fEnd.value === address) return;
    // Clear any existing chip-from
    document.querySelectorAll(".addr-chip.chip-from").forEach(c => c.classList.remove("chip-from"));
    chip.classList.add("chip-from");
    if (fStart) fStart.value = address;
    chipTarget = "end"; // advance target to To
  } else {
    // Mutual exclusion: can't be From and To
    if (fStart && fStart.value === address) return;
    // Clear any existing chip-to
    document.querySelectorAll(".addr-chip.chip-to").forEach(c => c.classList.remove("chip-to"));
    chip.classList.add("chip-to");
    if (fEnd) fEnd.value = address;
    // Keep chipTarget on "end" in case user wants to change
  }
}

// ── Add address ───────────────────────────────────────────────────────────────

document.getElementById("add-addr-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const label   = document.getElementById("new-addr-label").value.trim();
  const address = document.getElementById("new-addr-address").value.trim();

  const data = await addrFetch("/api/addresses", {
    method: "POST",
    body: JSON.stringify({ label, address }),
  });

  if (data.error) { addrFlash(data.error, "error"); return; }

  addAddrRow(data);
  e.target.reset();
  addrFlash(`"${data.label}" saved.`);
  syncAddressChips();
});

// ── Row rendering ─────────────────────────────────────────────────────────────

function addAddrRow(addr) {
  const tbody = document.getElementById("addr-tbody");
  const tr = document.createElement("tr");
  tr.dataset.id = addr.id;
  tr.innerHTML = addrRowHTML(addr);
  stashAddrData(tr, addr);
  tbody.appendChild(tr);
  bindAddrRowEvents(tr);
  updateAddrEmptyState();
}

function addrRowHTML(addr) {
  return `
    <td class="drag-handle" title="Drag to reorder">⠿</td>
    <td class="addr-label" style="font-weight:500;font-size:.84rem">${addrEsc(addr.label)}</td>
    <td class="addr-address" style="color:var(--muted);font-size:.84rem">${addrEsc(addr.address)}</td>
    <td style="display:flex;gap:.4rem;justify-content:flex-end">
      <button class="btn-edit">Edit</button>
      <button class="btn-delete">Delete</button>
    </td>`;
}

function addrEditRowHTML(addr) {
  return `
    <td class="drag-handle" title="Drag to reorder">⠿</td>
    <td><input class="inline-input inline-input--short" id="edit-addr-label" value="${addrEsc(addr.label)}" placeholder="Home"></td>
    <td><input class="inline-input" id="edit-addr-address" value="${addrEsc(addr.address)}" placeholder="123 Main St, City"></td>
    <td style="display:flex;gap:.4rem;justify-content:flex-end">
      <button class="btn-save">Save</button>
      <button class="btn-cancel">Cancel</button>
    </td>`;
}

function stashAddrData(tr, addr) {
  tr.dataset.label   = addr.label   ?? tr.querySelector(".addr-label")?.textContent?.trim()   ?? "";
  tr.dataset.address = addr.address ?? tr.querySelector(".addr-address")?.textContent?.trim() ?? "";
}

function bindAddrRowEvents(tr) {
  tr.querySelector(".btn-delete")?.addEventListener("click", () => handleAddrDelete(tr));
  tr.querySelector(".btn-edit")?.addEventListener("click",   () => handleAddrEditStart(tr));
  tr.querySelector(".btn-save")?.addEventListener("click",   () => handleAddrSave(tr));
  tr.querySelector(".btn-cancel")?.addEventListener("click", () => handleAddrCancel(tr));
  bindAddrDragEvents(tr);
}

// ── CRUD handlers ─────────────────────────────────────────────────────────────

async function handleAddrDelete(tr) {
  const label = tr.querySelector(".addr-label")?.textContent;
  if (!confirm(`Delete "${label}"?`)) return;
  const data = await addrFetch(`/api/addresses/${tr.dataset.id}`, { method: "DELETE" });
  if (data?.error) { addrFlash(data.error, "error"); return; }
  tr.remove();
  updateAddrEmptyState();
  addrFlash(`"${label}" deleted.`);
  syncAddressChips();
}

function handleAddrEditStart(tr) {
  const addr = {
    id:      tr.dataset.id,
    label:   tr.querySelector(".addr-label").textContent.trim(),
    address: tr.querySelector(".addr-address").textContent.trim(),
  };
  tr.innerHTML = addrEditRowHTML(addr);
  bindAddrRowEvents(tr);
  tr.querySelector("#edit-addr-label").focus();
}

async function handleAddrSave(tr) {
  const label   = tr.querySelector("#edit-addr-label").value.trim();
  const address = tr.querySelector("#edit-addr-address").value.trim();

  const data = await addrFetch(`/api/addresses/${tr.dataset.id}`, {
    method: "PATCH",
    body: JSON.stringify({ label, address }),
  });
  if (data.error) { addrFlash(data.error, "error"); return; }
  tr.innerHTML = addrRowHTML(data);
  stashAddrData(tr, data);
  bindAddrRowEvents(tr);
  addrFlash(`"${data.label}" saved.`);
  syncAddressChips();
}

function handleAddrCancel(tr) {
  const addr = {
    id:      tr.dataset.id,
    label:   tr.dataset.label,
    address: tr.dataset.address,
  };
  tr.innerHTML = addrRowHTML(addr);
  bindAddrRowEvents(tr);
}

// ── Drag-to-reorder ───────────────────────────────────────────────────────────

let addrDragSrc = null;

function bindAddrDragEvents(tr) {
  const handle = tr.querySelector(".drag-handle");
  if (!handle) return;

  handle.addEventListener("mousedown", () => { tr.draggable = true; });
  handle.addEventListener("mouseup",   () => { tr.draggable = false; });

  tr.addEventListener("dragstart", (e) => {
    addrDragSrc = tr;
    e.dataTransfer.effectAllowed = "move";
    setTimeout(() => tr.classList.add("dragging"), 0);
  });

  tr.addEventListener("dragend", () => {
    tr.draggable = false;
    tr.classList.remove("dragging");
    document.querySelectorAll("#addr-tbody tr").forEach(r => r.classList.remove("drag-over"));
    persistAddrOrder();
  });

  tr.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (addrDragSrc && addrDragSrc !== tr) {
      document.querySelectorAll("#addr-tbody tr").forEach(r => r.classList.remove("drag-over"));
      tr.classList.add("drag-over");
    }
  });

  tr.addEventListener("drop", (e) => {
    e.preventDefault();
    if (!addrDragSrc || addrDragSrc === tr) return;
    const tbody = tr.closest("tbody");
    const rows  = [...tbody.querySelectorAll("tr")];
    const srcIdx = rows.indexOf(addrDragSrc);
    const tgtIdx = rows.indexOf(tr);
    if (srcIdx < tgtIdx) tbody.insertBefore(addrDragSrc, tr.nextSibling);
    else                  tbody.insertBefore(addrDragSrc, tr);
    tr.classList.remove("drag-over");
  });
}

async function persistAddrOrder() {
  const ids = [...document.querySelectorAll("#addr-tbody tr")].map(tr => parseInt(tr.dataset.id));
  await addrFetch("/api/addresses/reorder", { method: "POST", body: JSON.stringify({ ids }) });
  syncAddressChips();
}

// ── Sync chips from current modal tbody ───────────────────────────────────────

function syncAddressChips() {
  const addresses = [...document.querySelectorAll("#addr-tbody tr")].map(tr => ({
    id:      parseInt(tr.dataset.id),
    label:   tr.dataset.label   || tr.querySelector(".addr-label")?.textContent?.trim()   || "",
    address: tr.dataset.address || tr.querySelector(".addr-address")?.textContent?.trim() || "",
  }));
  renderChips(addresses);
}

// ── Utils ─────────────────────────────────────────────────────────────────────

function addrEsc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function updateAddrEmptyState() {
  const empty = document.getElementById("addr-empty");
  const tbody = document.getElementById("addr-tbody");
  if (empty) empty.style.display = tbody.children.length === 0 ? "" : "none";
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.querySelectorAll("#addr-tbody tr").forEach(tr => {
  stashAddrData(tr, {});
  bindAddrRowEvents(tr);
});

syncAddressChips();
