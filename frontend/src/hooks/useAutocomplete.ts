import { useCallback, useRef, useState } from 'react';
import { apiFetch } from '../api';

interface Suggestion { label: string; lon: number | null; lat: number | null }

export function useAutocomplete() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [activeIdx, setActiveIdx] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const seqRef = useRef(0);

  const fetchSuggestions = useCallback((q: string) => {
    clearTimeout(debounceRef.current);
    if (q.trim().length < 2) { setSuggestions([]); return; }
    debounceRef.current = setTimeout(() => {
      const seq = ++seqRef.current;
      const url = `/autocomplete?q=${encodeURIComponent(q.trim())}`;
      apiFetch<Suggestion[]>(url)
        .then(data => { if (seq === seqRef.current) { setSuggestions(data); setActiveIdx(-1); } })
        .catch(() => {});
    }, 250);
  }, []);

  const clear = useCallback(() => { setSuggestions([]); setActiveIdx(-1); }, []);

  return { suggestions, activeIdx, setActiveIdx, fetchSuggestions, clear };
}
