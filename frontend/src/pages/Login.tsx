import { type FormEvent, useState } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const isSignup = location.pathname === '/signup';

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { signup } = useAuth();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isSignup) {
        await signup(username, password, password2);
      } else {
        await login(username, password);
      }
      navigate('/');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>{isSignup ? 'Create Account' : 'Sign in'}</h1>
        <p className="subtitle">
          {isSignup ? 'Join Undriven' : 'Welcome back to Undriven'}
        </p>

        {error && <div className="flash error">{error}</div>}

        <div className="form-field">
          <label>Username</label>
          <input
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            autoFocus
            required
          />
        </div>

        <div className="form-field">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />
        </div>

        {isSignup && (
          <div className="form-field">
            <label>Confirm Password</label>
            <input
              type="password"
              value={password2}
              onChange={e => setPassword2(e.target.value)}
              required
            />
          </div>
        )}

        <button className="btn-log" type="submit" disabled={loading}>
          {loading ? 'Loading...' : isSignup ? 'Create Account' : 'Sign in'}
        </button>

        <Link className="switch-link" to={isSignup ? '/login' : '/signup'}>
          {isSignup ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
        </Link>
      </form>
    </div>
  );
}
