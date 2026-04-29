import { type FormEvent, useState } from 'react';
import { apiFetch } from '../api';
import AutocompleteInput from './AutocompleteInput';

const MODES = ['bike', 'walk', 'train', 'bus', 'scooter', 'car', 'other'];

interface Segment {
  id: number;
  start: string;
  end: string;
  mode: string;
}

interface Car { id: number; name: string; mpg: number; fuel_type: string; is_default: boolean }
interface Address { id: number; label: string; address: string }

interface Props {
  cars: Car[];
  addresses: Address[];
  onLogged: () => void;
}

let segIdCounter = 1;

export default function LogForm({ cars, addresses, onLogged }: Props) {
  const [segments, setSegments] = useState<Segment[]>([
    { id: 0, start: '', end: '', mode: 'bike' },
  ]);
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [car, setCar] = useState(cars.find(c => c.is_default)?.name ?? '');
  const [notes, setNotes] = useState('');
  const [roundTrip, setRoundTrip] = useState(true);
  const [loading, setLoading] = useState(false);
  const [flash, setFlash] = useState<{ type: string; msg: string } | null>(null);

  const isMultiSegment = segments.length > 1;

  const updateSeg = (id: number, field: keyof Segment, val: string) => {
    setSegments(prev => prev.map(s => s.id === id ? { ...s, [field]: val } : s));
  };

  const addSegment = () => {
    const last = segments[segments.length - 1];
    setSegments(prev => [...prev, {
      id: segIdCounter++,
      start: last.end,
      end: '',
      mode: last.mode,
    }]);
  };

  const removeSegment = (id: number) => {
    setSegments(prev => prev.filter(s => s.id !== id));
  };

  const swapFirstSegment = () => {
    if (segments.length === 1) {
      const s = segments[0];
      setSegments([{ ...s, start: s.end, end: s.start }]);
    }
  };

  const handleChip = (address: string, target: 'from' | 'to') => {
    if (segments.length > 0) {
      const first = segments[0];
      if (target === 'from') {
        updateSeg(first.id, 'start', address);
      } else {
        updateSeg(first.id, 'end', address);
      }
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFlash(null);
    setLoading(true);

    try {
      const body: Record<string, unknown> = { date, car, notes, round_trip: roundTrip };

      if (isMultiSegment) {
        body.segments = segments.map(s => ({ start: s.start, end: s.end, mode: s.mode }));
        body.start = segments[0].start;
        body.end = segments[segments.length - 1].end;
        body.mode = segments[0].mode;
      } else {
        body.start = segments[0].start;
        body.end = segments[0].end;
        body.mode = segments[0].mode;
      }

      const res = await apiFetch<{ miles: number }>('/trips', { method: 'POST', body: JSON.stringify(body) });
      setFlash({ type: 'success', msg: `Trip logged! ${res.miles.toFixed(1)} mi` });
      setSegments([{ id: segIdCounter++, start: '', end: '', mode: 'bike' }]);
      setNotes('');
      setRoundTrip(true);
      onLogged();
    } catch (err: unknown) {
      setFlash({ type: 'error', msg: err instanceof Error ? err.message : 'Failed to log trip' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="log-card">
      <div className="form-header">
        <span className="form-title">Log a trip</span>
      </div>

      {flash && <div className={`flash ${flash.type}`}>{flash.msg}</div>}

      {addresses.length > 0 && (
        <div className="addr-chips">
          {addresses.map(a => (
            <span key={a.id} className="addr-chip" onClick={() => {
              const first = segments[0];
              if (!first.start) handleChip(a.address, 'from');
              else if (!first.end) handleChip(a.address, 'to');
              else handleChip(a.address, 'from');
            }}>
              {a.label}
            </span>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {segments.map((seg, i) => (
          <div key={seg.id} className={isMultiSegment ? 'segment-row' : 'route-row'}>
            <AutocompleteInput
              label={i === 0 ? 'From' : `From (leg ${i + 1})`}
              value={seg.start}
              onChange={val => updateSeg(seg.id, 'start', val)}
            />
            {!isMultiSegment && (
              <div className="route-divider">
                <button type="button" className="btn-swap" onClick={swapFirstSegment}>&#8596;</button>
              </div>
            )}
            <AutocompleteInput
              label={i === 0 ? 'To' : `To (leg ${i + 1})`}
              value={seg.end}
              onChange={val => updateSeg(seg.id, 'end', val)}
            />
            <div className="form-field">
              <label>Mode</label>
              <select value={seg.mode} onChange={e => updateSeg(seg.id, 'mode', e.target.value)}>
                {MODES.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            {isMultiSegment && (
              <button type="button" className="btn-remove-seg" onClick={() => removeSegment(seg.id)}>
                &#10005;
              </button>
            )}
          </div>
        ))}

        <button type="button" className="btn-add-seg" onClick={addSegment}>+ Add segment</button>

        <div className="form-divider" />

        <div className="meta-row">
          <div className="form-field">
            <label>Date</label>
            <input type="date" value={date} onChange={e => setDate(e.target.value)} required />
          </div>
          <div className="form-field">
            <label>Car replaced</label>
            <select value={car} onChange={e => setCar(e.target.value)}>
              <option value="">None</option>
              {cars.map(c => <option key={c.id} value={c.name}>{c.name} ({c.mpg} mpg)</option>)}
            </select>
          </div>
          <div className="form-field">
            <label>Notes</label>
            <input type="text" value={notes} onChange={e => setNotes(e.target.value)} placeholder="optional" />
          </div>
        </div>

        <div className="form-actions">
          {!isMultiSegment ? (
            <div className="trip-toggle">
              <button type="button" className={`tt-btn${roundTrip ? ' active' : ''}`} onClick={() => setRoundTrip(true)}>Round trip</button>
              <button type="button" className={`tt-btn${!roundTrip ? ' active' : ''}`} onClick={() => setRoundTrip(false)}>One way</button>
            </div>
          ) : <div />}
          <button type="submit" className="btn-log" disabled={loading}>
            {loading ? 'Logging...' : 'Log trip'}
          </button>
        </div>
      </form>
    </div>
  );
}
