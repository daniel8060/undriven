import { useRef } from 'react';
import { useAutocomplete } from '../hooks/useAutocomplete';

interface Props {
  value: string;
  onChange: (val: string) => void;
  label: string;
  placeholder?: string;
}

export default function AutocompleteInput({ value, onChange, label, placeholder }: Props) {
  const { suggestions, activeIdx, setActiveIdx, fetchSuggestions, clear } = useAutocomplete();
  const wrapRef = useRef<HTMLDivElement>(null);

  const handleSelect = (text: string) => {
    onChange(text);
    clear();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!suggestions.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIdx(Math.min(activeIdx + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIdx(Math.max(activeIdx - 1, -1));
    } else if (e.key === 'Enter' && activeIdx >= 0) {
      e.preventDefault();
      handleSelect(suggestions[activeIdx].label);
    } else if (e.key === 'Escape') {
      clear();
    }
  };

  return (
    <div className="form-field">
      <label>{label}</label>
      <div className="ac-wrap" ref={wrapRef}>
        <input
          type="text"
          value={value}
          placeholder={placeholder}
          onChange={e => { onChange(e.target.value); fetchSuggestions(e.target.value); }}
          onKeyDown={handleKeyDown}
          onBlur={() => setTimeout(clear, 150)}
        />
        {suggestions.length > 0 && (
          <div className="ac-dropdown">
            {suggestions.map((s, i) => (
              <div
                key={i}
                className={`ac-item${i === activeIdx ? ' active' : ''}`}
                onMouseDown={e => { e.preventDefault(); handleSelect(s.label); }}
              >
                {s.label}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
