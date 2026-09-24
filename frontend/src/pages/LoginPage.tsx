import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ArrowRight, ArrowLeft } from 'lucide-react';

export function LoginPage() {
  useEffect(() => { document.title = 'Sign In — FlowAlchemy'; }, []);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg p-4">
      <div className="w-full max-w-md animate-fade-in">
        {/* Back to home */}
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors mb-6"
        >
          <ArrowLeft size={14} />
          Back to home
        </Link>

        {/* Logo */}
        <div className="text-center mb-8">
          <img src="/logo.svg" alt="FlowAlchemy" className="w-12 h-12 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-text-primary font-heading">FlowAlchemy</h1>
          <p className="text-text-muted mt-2">Visual Workflow Automation</p>
        </div>

        {/* Card */}
        <div className="bg-surface border border-border rounded-2xl p-8 shadow-lg">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-text-primary">Welcome back</h2>
            <p className="text-sm text-text-muted mt-1">Sign in to continue to your workflows</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 bg-error-bg border border-error/50 rounded-xl text-error-text text-sm animate-shake">
                {error}
              </div>
            )}

            <div className="space-y-2">
              <label htmlFor="email" className="block text-sm font-medium text-text-secondary">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="w-full px-4 py-3 bg-bg border border-border rounded-xl text-text-primary placeholder:text-text-muted focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all duration-200"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="password" className="block text-sm font-medium text-text-secondary">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                className="w-full px-4 py-3 bg-bg border border-border rounded-xl text-text-primary placeholder:text-text-muted focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all duration-200"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 bg-primary hover:bg-primary-hover text-white font-semibold rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2 group"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Sign In
                  <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center mt-6 text-text-muted text-sm">
          Don't have an account?{' '}
          <Link
            to="/register"
            className="text-primary hover:text-primary-hover font-medium transition-colors"
          >
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
