import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api';
import LogForm from '../components/LogForm';
import SummaryCards from '../components/SummaryCards';
import WeeklyChart from '../components/WeeklyChart';
import CarsModal from '../components/CarsModal';
import AddressesModal from '../components/AddressesModal';

interface Summary {
  total_miles: number;
  total_co2_kg: number;
  total_trips: number;
  top_mode: string;
  by_mode: { mode: string; miles: number; trips: number }[];
  by_car: { car_name: string; miles: number; co2_kg: number }[];
  over_time: { week: string; miles: number; trips: number; by_mode: Record<string, number> }[];
}

interface Car { id: number; name: string; mpg: number; fuel_type: string; is_default: boolean }
interface Address { id: number; label: string; address: string }

export default function Dashboard() {
  const { logout } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [cars, setCars] = useState<Car[]>([]);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [carsOpen, setCarsOpen] = useState(false);
  const [addrsOpen, setAddrsOpen] = useState(false);

  const loadAll = useCallback(async () => {
    const [s, c, a] = await Promise.all([
      apiFetch<Summary>('/summary'),
      apiFetch<Car[]>('/cars'),
      apiFetch<Address[]>('/addresses'),
    ]);
    setSummary(s);
    setCars(c);
    setAddresses(a);
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  if (!summary) return null;

  const maxMiles = Math.max(...summary.by_mode.map(m => m.miles), 1);

  return (
    <div className="page">
      <header className="header">
        <div className="header-left">
          <h1>Undriven</h1>
          <p>miles replaced by non-car trips</p>
        </div>
        <nav style={{ display: 'flex', gap: '1.25rem', alignItems: 'center' }}>
          <button onClick={() => setAddrsOpen(true)} style={{ background: 'none', border: 'none', fontFamily: 'var(--sans)', fontSize: '.85rem', color: 'var(--accent)', cursor: 'pointer', padding: 0 }}>Addresses</button>
          <button onClick={() => setCarsOpen(true)} style={{ background: 'none', border: 'none', fontFamily: 'var(--sans)', fontSize: '.85rem', color: 'var(--accent)', cursor: 'pointer', padding: 0 }}>Cars</button>
          <Link to="/trips" style={{ fontSize: '.85rem', color: 'var(--muted)' }}>Trip History</Link>
          <button onClick={logout} style={{ background: 'none', border: 'none', fontFamily: 'var(--sans)', fontSize: '.85rem', color: 'var(--muted)', cursor: 'pointer', padding: 0 }}>Sign out</button>
        </nav>
      </header>

      <LogForm cars={cars} addresses={addresses} onLogged={loadAll} />

      <SummaryCards summary={summary} />

      <div className="charts-row">
        <div className="card">
          <div className="card-title">Weekly miles (last 12 weeks)</div>
          <WeeklyChart weeks={summary.over_time} />
        </div>
        <div className="card">
          <div className="card-title">By mode</div>
          <div className="mode-rows">
            {summary.by_mode.map(m => (
              <div key={m.mode} className="mode-row">
                <span className="mode-label">{m.mode}</span>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{
                      width: `${(m.miles / maxMiles) * 100}%`,
                      background: `var(--mode-${m.mode})`,
                    }}
                  />
                </div>
                <span className="mode-val">{m.miles.toFixed(1)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <CarsModal open={carsOpen} onClose={() => setCarsOpen(false)} onUpdated={loadAll} />
      <AddressesModal open={addrsOpen} onClose={() => setAddrsOpen(false)} onUpdated={loadAll} />
    </div>
  );
}
