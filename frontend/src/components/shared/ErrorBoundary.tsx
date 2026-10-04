import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error caught by VARUNA ErrorBoundary:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[400px] w-full p-6 flex flex-col items-center justify-center bg-surface border border-red-500/30 rounded-xl m-4 text-center">
          <div className="w-12 h-12 rounded-full bg-red-950/60 border border-red-500/50 flex items-center justify-center text-red-400 mb-4">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h2 className="font-headline font-bold text-xl text-slate-100 mb-2">
            Component Render Exception Prevented
          </h2>
          <p className="text-xs font-mono text-slate-400 max-w-md mb-4">
            An unexpected error occurred while rendering this viewport view. The exception was safely trapped by VARUNA's boundary shield.
          </p>
          {this.state.error && (
            <div className="p-3 bg-slate-950 rounded border border-red-900/40 text-left font-mono text-[11px] text-red-300 max-w-xl w-full overflow-x-auto mb-5">
              {this.state.error.toString()}
            </div>
          )}
          <button
            onClick={this.handleReset}
            className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold font-mono text-xs flex items-center gap-2 transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reload Workspace View
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
