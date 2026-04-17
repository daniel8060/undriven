import { type FormEvent, useEffect, useState } from 'react';
import { apiFetch } from '../api';

interface Car {
  id: number;
  name: string;
  mpg: number;
  fuel_type: string;
  is_default: boolean;
}

interface Props {
  open: boolean;
  onClose: () => void;
  onUpdated: () => void;
}

export default function CarsModal({ open, onClose, onUpdated }: Props) {
  const [cars, setCars] = useState<Car[]>([]);
  const [name, setName] = useState('');
  const [mpg, setMpg] = useState('');
  const [fuelType, setFuelType] = useState('gasoline');
  const [flash, setFlash] = useState<{ type: string; msg: string } | null>(null);

  const load = async () => {
    const data = await apiFetch<Car[]>('/cars');
    setCars(data);
  };

  useEffect(() => { if (open) load(); }, [open]);

  const showFlash = (msg: string, type = 'success') => {
    setFlash({ type, msg });
    setTimeout(() => setFlash(null), 4000);
  };

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !mpg) return;
    try {
      await apiFetch('/cars', {
        method: 'POST',
        body: JSON.stringify({ name: name.trim(), mpg: parseFloat(mpg), fuel_type: fuelType }),
      });
      setName(''); setMpg(''); setFuelType('gasoline');
      showFlash('Car added');
      load();
      onUpdated();
    } catch (err: unknown) {
      showFlash(err instanceof Error ? err.message : 'Error', 'error');
    }
  };

  const handleDelete = async (id: number) => {
    await apiFetch(`/cars/${id}`, { method: 'DELETE' });
    showFlash('Car deleted');
    load();
    onUpdated();
  };

  const handleSetDefault = async (id: number) => {
    await apiFetch(`/cars/${id}/set-default`, { method: 'POST' });
    load();
    onUpdated();
  };

  if (!open) return null;

  return (
    <div className="modal-backdrop open" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Saved Cars</h2>
          <button className="modal-close" onClick={onClose}>{'\u00D7'}</button>
        </div>
        <div className="modal-body">
          {flash && <div className={`modal-flash ${flash.type}`}>{flash.msg}</div>}

          <form className="modal-add-row" onSubmit={handleAdd}>
            <div className="form-field">
              <label>Name</label>
              <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Corolla" />
            </div>
            <div className="form-field">
              <label>MPG</label>
              <input type="number" step="0.1" value={mpg} onChange={e => setMpg(e.target.value)} />
            </div>
            <div className="form-field">
              <label>Fuel</label>
              <select value={fuelType} onChange={e => setFuelType(e.target.value)}>
                <option value="gasoline">Gasoline</option>
                <option value="diesel">Diesel</option>
                <option value="hybrid">Hybrid</option>
                <option value="electric">Electric</option>
              </select>
            </div>
            <button type="submit" className="btn-log" style={{ alignSelf: 'end' }}>Add</button>
          </form>

          {cars.map(car => (
            <div key={car.id} className="reorder-item">
              <div className="reorder-item-info">
                <strong>{car.name}</strong> — {car.mpg} mpg, {car.fuel_type}
                {car.is_default && <span style={{ marginLeft: '.5rem', fontSize: '.75rem', color: 'var(--accent)' }}>(default)</span>}
              </div>
              <div className="reorder-item-actions">
                {!car.is_default && (
                  <button className="btn-inline" onClick={() => handleSetDefault(car.id)}>Default</button>
                )}
                <button className="btn-inline danger" onClick={() => handleDelete(car.id)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
