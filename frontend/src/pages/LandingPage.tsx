import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Blocks,
  Zap,
  Shield,
  Clock,
  GitBranch,
  Eye,
  ChevronRight,
  Play,
  Settings,
} from 'lucide-react';

export function LandingPage() {
  useEffect(() => { document.title = 'FlowAlchemy — Visual Workflow Automation'; }, []);
  const features = [
    {
      icon: Blocks,
      title: 'Drag & Drop Builder',
      description:
        'Build workflows visually by connecting nodes. No coding required — just drag, drop, and configure.',
    },
    {
      icon: Zap,
      title: 'Async Execution',
      description:
        'Workflows run asynchronously with Redis-powered job queues. Handle retries, timeouts, and parallel execution.',
    },
    {
      icon: GitBranch,
      title: 'Version Control',
      description:
        'Every change is tracked. Compare versions, revert to previous states, and replay any workflow version.',
    },
    {
      icon: Shield,
      title: 'Secure Credentials',
      description:
        'API keys and secrets are encrypted at rest. Credentials are managed separately from workflow logic.',
    },
    {
      icon: Eye,
      title: 'Visual Debugger',
      description:
        'Step through executions, inspect node outputs, and find issues fast with real-time debugging.',
    },
    {
      icon: Clock,
      title: 'Scheduling & Webhooks',
      description:
        'Run workflows on cron schedules or trigger them via webhook. Automate anything, anytime.',
    },
  ];

  const nodeTypes = [
    { name: 'HTTP Request', color: 'bg-info-bg text-info' },
    { name: 'Transform', color: 'bg-accent-bg text-accent' },
    { name: 'Condition', color: 'bg-warning-bg text-warning-text' },
    { name: 'Delay', color: 'bg-surface-hover text-text-secondary' },
    { name: 'Webhook', color: 'bg-primary-bg text-primary' },
    { name: 'Output', color: 'bg-error-bg text-error-text' },
  ];

  return (
    <div className="min-h-screen bg-bg">
      {/* Nav */}
      <nav className="border-b border-border bg-surface/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/logo.svg" alt="FlowAlchemy" className="w-8 h-8" />
            <span className="text-lg font-bold text-text-primary font-heading">FlowAlchemy</span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/login"
              className="px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors"
            >
              Sign In
            </Link>
            <Link
              to="/register"
              className="px-4 py-2 text-sm font-medium bg-primary hover:bg-primary-hover text-white rounded-xl transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 pt-20 pb-16 text-center">
        <div className="animate-fade-in-up">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-primary/10 border border-primary/20 rounded-full text-primary text-sm font-medium mb-6">
            <Zap size={14} />
            Visual Workflow Automation
          </div>

          <h1 className="text-5xl md:text-6xl font-bold text-text-primary font-heading leading-tight">
            Build workflows
            <br />
            <span className="text-primary">without code</span>
          </h1>

          <p className="mt-6 text-lg text-text-secondary max-w-2xl mx-auto leading-relaxed">
            FlowAlchemy lets you design, execute, and monitor automated workflows using a visual
            drag-and-drop editor. Connect APIs, transform data, and orchestrate complex
            processes — all in your browser.
          </p>

          <div className="mt-8 flex items-center justify-center gap-4">
            <Link
              to="/register"
              className="px-6 py-3 bg-primary hover:bg-primary-hover text-white font-semibold rounded-xl transition-all duration-200 flex items-center gap-2 group"
            >
              Start Building Free
              <ArrowRight
                size={18}
                className="group-hover:translate-x-1 transition-transform"
              />
            </Link>
            <Link
              to="/login"
              className="px-6 py-3 border border-border hover:border-border-hover text-text-secondary hover:text-text-primary font-medium rounded-xl transition-all duration-200"
            >
              Sign In
            </Link>
          </div>
        </div>

        {/* Editor preview */}
        <div className="mt-16 animate-fade-in-up" style={{ animationDelay: '200ms' }}>
          <div className="bg-surface border border-border rounded-2xl p-4 shadow-2xl max-w-4xl mx-auto">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-3 h-3 rounded-full bg-red-500/80" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
              <div className="w-3 h-3 rounded-full bg-green-500/80" />
              <span className="ml-2 text-xs text-text-muted font-mono">workflow-editor</span>
            </div>
            <div className="bg-bg rounded-xl p-6 border border-border">
              <div className="flex items-center gap-4 justify-center flex-wrap">
                {/* Mini node preview */}
                {nodeTypes.map((node, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <div
                      className={`px-3 py-2 rounded-lg border border-border text-xs font-medium ${node.color}`}
                    >
                      {node.name}
                    </div>
                    {i < nodeTypes.length - 1 && (
                      <ChevronRight size={14} className="text-text-muted" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-4 py-20">
        <div className="text-center mb-12 animate-fade-in-up">
          <h2 className="text-3xl font-bold text-text-primary font-heading">
            Everything you need
          </h2>
          <p className="mt-3 text-text-secondary">
            A complete toolkit for building and running automated workflows
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 stagger-children">
          {features.map((feature, i) => (
            <div
              key={i}
              className="p-5 bg-surface border border-border rounded-2xl hover:border-border-hover transition-all duration-200 group"
            >
              <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                <feature.icon size={20} className="text-primary" />
              </div>
              <h3 className="text-lg font-semibold text-text-primary font-heading">
                {feature.title}
              </h3>
              <p className="mt-2 text-sm text-text-secondary leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-border bg-surface/50">
        <div className="max-w-6xl mx-auto px-4 py-20">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-text-primary font-heading">
              How it works
            </h2>
            <p className="mt-3 text-text-secondary">
              Three steps to automate anything
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 stagger-children">
            {[
              {
                step: '01',
                title: 'Design',
                desc: 'Drag nodes from the palette and connect them to build your workflow visually.',
                icon: Blocks,
              },
              {
                step: '02',
                title: 'Configure',
                desc: 'Click any node to set its parameters — URLs, expressions, conditions, and more.',
                icon: Settings,
              },
              {
                step: '03',
                title: 'Execute',
                desc: 'Run your workflow instantly or schedule it. Monitor execution in real-time.',
                icon: Play,
              },
            ].map((item, i) => (
              <div key={i} className="text-center">
                <div className="text-5xl font-bold text-primary/20 font-heading mb-4">
                  {item.step}
                </div>
                <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <item.icon size={24} className="text-primary" />
                </div>
                <h3 className="text-lg font-semibold text-text-primary font-heading">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm text-text-secondary">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-6xl mx-auto px-4 py-20">
        <div className="bg-primary/10 border border-primary/20 rounded-3xl p-12 text-center">
          <h2 className="text-3xl font-bold text-text-primary font-heading">
            Ready to automate?
          </h2>
          <p className="mt-3 text-text-secondary max-w-lg mx-auto">
            Create your first workflow in minutes. No credit card required.
          </p>
          <Link
            to="/register"
            className="inline-flex items-center gap-2 mt-8 px-6 py-3 bg-primary hover:bg-primary-hover text-white font-semibold rounded-xl transition-all duration-200 group"
          >
            Get Started Free
            <ArrowRight
              size={18}
              className="group-hover:translate-x-1 transition-transform"
            />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="max-w-6xl mx-auto px-4 py-8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img src="/logo.svg" alt="FlowAlchemy" className="w-5 h-5" />
            <span className="text-sm text-text-muted">FlowAlchemy</span>
          </div>
          <p className="text-sm text-text-muted">
            Visual Workflow Automation Engine
          </p>
        </div>
      </footer>
    </div>
  );
}
