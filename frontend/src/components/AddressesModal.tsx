import { type FormEvent, useEffect, useState } from 'react';
import { apiFetch } from '../api';

interface Address {
  id: number;
  label: string;
  address: string;
}

interface Props {
  open: boolean;
  onClose: () => void;
  onUpdated: () => void;
}

export default function AddressesModal({ open, onClose, onUpdated }: Props) {
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [label, setLabel] = useState('');
  const [address, setAddress] = useState('');
  const [flash, setFlash] = useState<{ type: string; msg: string } | null>(null);

  const load = async () => {
    const data = await apiFetch<Address[]>('/addresses');
    setAddresses(data);
  };

  useEffect(() => { if (open) load(); }, [open]);

  const showFlash = (msg: string, type = 'success') => {
    setFlash({ type, msg });
    setTimeout(() => setFlash(null), 4000);
  };

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault();
    if (!label.trim() || !address.trim()) return;
    try {
      await apiFetch('/addresses', {
        method: 'POST',
        body: JSON.stringify({ label: label.trim(), address: address.trim() }),
      });
      setLabel(''); setAddress('');
      showFlash('Address saved');
      load();
      onUpdated();
    } catch (err: unknown) {
      showFlash(err instanceof Error ? err.message : 'Error', 'error');
    }
  };

  const handleDelete = async (id: number) => {
    await apiFetch(`/addresses/${id}`, { method: 'DELETE' });
    showFlash('Address deleted');
    load();
    onUpdated();
  };

  if (!open) return null;

  return (
    <div className="modal-backdrop open" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Saved Addresses</h2>
          <button className="modal-close" onClick={onClose}>{'\u00D7'}</button>
        </div>
        <div className="modal-body">
          {flash && <div className={`modal-flash ${flash.type}`}>{flash.msg}</div>}

          <form className="modal-add-row" onSubmit={handleAdd} style={{ gridTemplateColumns: '1fr 2fr auto' }}>
            <div className="form-field">
              <label>Label</label>
              <input value={label} onChange={e => setLabel(e.target.value)} placeholder="e.g. Home" />
            </div>
            <div className="form-field">
              <label>Address</label>
              <input value={address} onChange={e => setAddress(e.target.value)} placeholder="Full address" />
            </div>
            <button type="submit" className="btn-log" style={{ alignSelf: 'end' }}>Add</button>
          </form>

          {addresses.map(a => (
            <div key={a.id} className="reorder-item">
              <div className="reorder-item-info">
                <strong>{a.label}</strong> — <span style={{ color: 'var(--muted)', fontSize: '.82rem' }}>{a.address}</span>
              </div>
              <div className="reorder-item-actions">
                <button className="btn-inline danger" onClick={() => handleDelete(a.id)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
