import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api';
import TripTable from '../components/TripTable';
import CarsModal from '../components/CarsModal';
import AddressesModal from '../components/AddressesModal';

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

export default function Trips() {
  const { logout } = useAuth();
  const [trips, setTrips] = useState<Trip[]>([]);
  const [carsOpen, setCarsOpen] = useState(false);
  const [addrsOpen, setAddrsOpen] = useState(false);

  const load = useCallback(async () => {
    const data = await apiFetch<Trip[]>('/trips');
    setTrips(data);
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="page">
      <header className="header">
        <div className="header-left">
          <h1>Trip History</h1>
          <p>all logged trips, most recent first</p>
        </div>
        <nav style={{ display: 'flex', gap: '1.25rem', alignItems: 'center' }}>
          <button onClick={() => setAddrsOpen(true)} style={{ background: 'none', border: 'none', fontFamily: 'var(--sans)', fontSize: '.85rem', color: 'var(--accent)', cursor: 'pointer', padding: 0 }}>Addresses</button>
          <button onClick={() => setCarsOpen(true)} style={{ background: 'none', border: 'none', fontFamily: 'var(--sans)', fontSize: '.85rem', color: 'var(--accent)', cursor: 'pointer', padding: 0 }}>Cars</button>
          <Link to="/" style={{ fontSize: '.85rem', color: 'var(--muted)' }}>{'\u2190'} Dashboard</Link>
          <button onClick={logout} style={{ background: 'none', border: 'none', fontFamily: 'var(--sans)', fontSize: '.85rem', color: 'var(--muted)', cursor: 'pointer', padding: 0 }}>Sign out</button>
        </nav>
      </header>

      <div className="card">
        <TripTable trips={trips} onDeleted={load} />
      </div>

      <CarsModal open={carsOpen} onClose={() => setCarsOpen(false)} onUpdated={load} />
      <AddressesModal open={addrsOpen} onClose={() => setAddrsOpen(false)} onUpdated={load} />
    </div>
  );
}
