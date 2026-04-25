import { useState } from 'react';
import { apiFetch } from '../api';

interface Segment {
  id: number;
  position: number;
  start_loc: string;
  end_loc: string;
  mode: string;
  miles: number;
}

interface Trip {
  id: number;
  date: string;
  start_loc: string;
  end_loc: string;
  mode: string;
  car_name: string | null;
  miles: number;
  co2_kg: number;
  notes: string | null;
  segments: Segment[];
}

interface Props {
  trips: Trip[];
  onDeleted: () => void;
}

export default function TripTable({ trips, onDeleted }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggle = (id: number) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this trip?')) return;
    await apiFetch(`/trips/${id}`, { method: 'DELETE' });
    onDeleted();
  };

  if (!trips.length) {
    return (
      <div className="empty-state">
        <strong>No trips logged yet.</strong>
        <p><a href="/">Log your first trip</a></p>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Route</th>
            <th>Mode</th>
            <th>Car</th>
            <th>Miles</th>
            <th>CO2 saved</th>
            <th>Notes</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {trips.map(trip => (
            <>
              <tr
                key={trip.id}
                className={trip.segments.length > 0 ? 'trip-has-segs' : ''}
                onClick={trip.segments.length > 0 ? () => toggle(trip.id) : undefined}
              >
                <td className="mono" style={{ whiteSpace: 'nowrap' }}>{trip.date}</td>
                <td>
                  <div className="route-cell">
                    <span className="endpoint">{trip.start_loc}</span>
                    <span className="arrow">{'\u2193'}</span>
                    <span className="endpoint">{trip.end_loc}</span>
                  </div>
                  {trip.segments.length > 0 && (
                    <span className="seg-count-badge">{trip.segments.length} segments</span>
                  )}
                </td>
                <td><span className={`mode-badge ${trip.mode}`}>{trip.mode}</span></td>
                <td style={{ color: 'var(--muted)', fontSize: '.84rem' }}>
                  {trip.car_name || '\u2014'}
                </td>
                <td className="mono">{trip.miles.toFixed(1)}</td>
                <td className="mono">
                  {trip.co2_kg > 0 ? `${trip.co2_kg.toFixed(2)} kg` : '\u2014'}
                </td>
                <td style={{ color: 'var(--muted)', fontSize: '.84rem', maxWidth: '140px' }}>
                  {trip.notes || ''}
                </td>
                <td>
                  <button
                    className="btn-delete"
                    onClick={e => { e.stopPropagation(); handleDelete(trip.id); }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
              {trip.segments.length > 0 && expanded.has(trip.id) && (
                <tr key={`seg-${trip.id}`}>
                  <td colSpan={8}>
                    <div className="seg-detail">
                      {trip.segments.map(seg => (
                        <div key={seg.id} className="seg-leg">
                          <span className={`mode-badge ${seg.mode}`}>{seg.mode}</span>
                          {seg.start_loc} {'\u2192'} {seg.end_loc}
                          <span className="seg-miles">{seg.miles.toFixed(1)} mi</span>
                        </div>
                      ))}
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}
