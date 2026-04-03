// Depends on: userFocus (declared in form.js, loaded before this file)

function setupAutocomplete(inputId, dropdownId) {
  const input    = document.getElementById(inputId);
  const dropdown = document.getElementById(dropdownId);
  let debounce   = null;
  let activeIdx  = -1;

  function showSuggestions(items) {
    dropdown.innerHTML = '';
    activeIdx = -1;
    items.forEach((item) => {
      const el = document.createElement('div');
      el.className = 'ac-item';
      el.textContent = item.label;
      el.addEventListener('mousedown', (e) => {
        e.preventDefault();
        input.value = item.label;
        dropdown.innerHTML = '';
      });
      dropdown.appendChild(el);
    });
  }

  input.addEventListener('input', () => {
    clearTimeout(debounce);
    const q = input.value.trim();
    if (q.length < 2) { dropdown.innerHTML = ''; return; }
    debounce = setTimeout(() => {
      let url = `/api/autocomplete?q=${encodeURIComponent(q)}`;
      if (userFocus) url += `&lon=${userFocus.lon}&lat=${userFocus.lat}`;
      fetch(url).then(r => r.json()).then(showSuggestions).catch(() => {});
    }, 250);
  });

  input.addEventListener('keydown', (e) => {
    const items = dropdown.querySelectorAll('.ac-item');
    if (!items.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIdx = Math.min(activeIdx + 1, items.length - 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIdx = Math.max(activeIdx - 1, -1);
    } else if (e.key === 'Enter' && activeIdx >= 0) {
      e.preventDefault();
      input.value = items[activeIdx].textContent;
      dropdown.innerHTML = '';
      return;
    } else if (e.key === 'Escape') {
      dropdown.innerHTML = '';
      return;
    }
    items.forEach((el, i) => el.classList.toggle('active', i === activeIdx));
    if (activeIdx >= 0) items[activeIdx].scrollIntoView({ block: 'nearest' });
  });

  input.addEventListener('blur', () => {
    setTimeout(() => { dropdown.innerHTML = ''; }, 150);
  });
}

setupAutocomplete('f-start', 'ac-start');
setupAutocomplete('f-end',   'ac-end');
