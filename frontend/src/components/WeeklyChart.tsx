import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend);

const MODE_COLORS: Record<string, string> = {
  bike:    'rgba(200, 87,  42,  0.85)',
  walk:    'rgba(59,  107, 69,  0.85)',
  train:   'rgba(46,  91,  138, 0.85)',
  bus:     'rgba(107, 74,  138, 0.85)',
  scooter: 'rgba(196, 160, 32,  0.85)',
  car:     'rgba(90,  90,  90,  0.85)',
  other:   'rgba(122, 58,  58,  0.85)',
};
const MODES = Object.keys(MODE_COLORS);

interface WeekData {
  week: string;
  miles: number;
  trips: number;
  by_mode: Record<string, number>;
}

export default function WeeklyChart({ weeks }: { weeks: WeekData[] }) {
  const data = {
    labels: weeks.map(w => w.week),
    datasets: MODES.map(mode => ({
      label: mode,
      data: weeks.map(w => w.by_mode?.[mode] ?? 0),
      backgroundColor: MODE_COLORS[mode],
      borderColor: MODE_COLORS[mode].replace('0.85', '1'),
      borderWidth: 1,
      borderRadius: 2,
      stack: 'miles',
    })),
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          title: (items: { dataIndex: number }[]) => {
            const w = weeks[items[0].dataIndex];
            return `${w.week}  ·  ${w.trips} trip${w.trips !== 1 ? 's' : ''}`;
          },
          label: (ctx: { parsed: { y: number }; dataset: { label?: string } }) => {
            const v = ctx.parsed.y;
            return v > 0 ? ` ${ctx.dataset.label}: ${v.toFixed(1)} mi` : null;
          },
          footer: (items: { dataIndex: number }[]) => {
            const total = weeks[items[0].dataIndex].miles;
            return total > 0 ? `Total: ${total.toFixed(1)} mi` : '';
          },
        },
      },
    },
    scales: {
      x: {
        stacked: true,
        grid: { display: false },
        ticks: {
          font: { family: "'JetBrains Mono', monospace", size: 10 },
          color: '#6b6660',
          maxRotation: 45,
        },
      },
      y: {
        stacked: true,
        beginAtZero: true,
        grid: { color: '#e0ddd7' },
        ticks: {
          font: { family: "'JetBrains Mono', monospace", size: 10 },
          color: '#6b6660',
        },
      },
    },
  } as const;

  return (
    <div className="chart-wrap">
      <Bar data={data} options={options as never} />
    </div>
  );
}
