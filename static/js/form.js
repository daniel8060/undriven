// ── Date: use local timezone, not UTC ──
(function () {
  const now = new Date();
  const y   = now.getFullYear();
  const m   = String(now.getMonth() + 1).padStart(2, '0');
  const d   = String(now.getDate()).padStart(2, '0');
  document.getElementById('f-date').value = `${y}-${m}-${d}`;
})();

// ── Geolocation — calibrates autocomplete to user's area ──
// userFocus is read by autocomplete.js
let userFocus = null;

document.getElementById('btn-locate').addEventListener('click', () => {
  if (!navigator.geolocation) { alert('Geolocation not supported by your browser.'); return; }
  const btn   = document.getElementById('btn-locate');
  const label = document.getElementById('locate-label');
  btn.classList.add('loading');
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      userFocus = { lon: pos.coords.longitude, lat: pos.coords.latitude };
      btn.classList.remove('loading');
      btn.classList.add('active');
      label.textContent = 'Location active';
    },
    () => {
      btn.classList.remove('loading');
      alert('Location access denied or unavailable.');
    }
  );
});

// ── Swap From / To ──
document.getElementById('btn-swap').addEventListener('click', () => {
  const a = document.getElementById('f-start');
  const b = document.getElementById('f-end');
  [a.value, b.value] = [b.value, a.value];

  const aLon = document.getElementById('f-start-lon');
  const aLat = document.getElementById('f-start-lat');
  const bLon = document.getElementById('f-end-lon');
  const bLat = document.getElementById('f-end-lat');
  [aLon.value, bLon.value] = [bLon.value, aLon.value];
  [aLat.value, bLat.value] = [bLat.value, aLat.value];
});

// ── Round trip toggle ──
const hiddenRT     = document.getElementById('f-round-trip');
const btnOneway    = document.getElementById('btn-oneway');
const btnRoundtrip = document.getElementById('btn-roundtrip');

btnOneway.addEventListener('click', () => {
  hiddenRT.value = '0';
  btnOneway.classList.add('active');
  btnRoundtrip.classList.remove('active');
});

btnRoundtrip.addEventListener('click', () => {
  hiddenRT.value = '1';
  btnRoundtrip.classList.add('active');
  btnOneway.classList.remove('active');
});

// ── Spinner on submit ──
document.querySelector('form[action="/log"]').addEventListener('submit', function () {
  document.getElementById('spinnerOverlay').classList.add('active');
});
