/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  // Classes built dynamically (e.g. `bg-${colorClass}` in FusionCentrePage) are invisible to the JIT scanner
  safelist: [
    { pattern: /^(bg|text|border)-(primary|secondary|tertiary|outline|error)$/ },
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--surface)',
        surface: {
          DEFAULT: 'var(--surface)',
          deep: 'var(--surface-deep)',
          panel: 'var(--surface-panel)',
          card: 'var(--surface-card)',
          cardHover: 'var(--surface-card-hover)',
          border: 'var(--surface-border)',
          borderBright: 'var(--surface-border-bright)',
          light: '#f8fafc',
          lightPanel: '#ffffff',
          lightBorder: '#e2e8f0'
        },
        primary: {
          DEFAULT: 'var(--primary-val)',
          hover: 'var(--primary-hover-val)',
          dark: 'var(--primary-dark-val)',
          glow: 'rgba(0, 229, 255, 0.25)'
        },
        meta: {
          DEFAULT: '#818cf8',
          dark: '#6366f1'
        },
        verified: {
          DEFAULT: '#10b981',
          bg: 'rgba(16, 185, 129, 0.15)',
          border: '#059669'
        },
        divergence: {
          DEFAULT: '#f59e0b',
          bg: 'rgba(245, 158, 11, 0.15)',
          border: '#d97706'
        },
        alert: {
          DEFAULT: '#ef4444',
          bg: 'rgba(239, 68, 68, 0.15)',
          border: '#dc2626'
        },
        // Scientific Precision tokens from DESIGN.md mapped dynamically
        "surface-container-high": "var(--surface-container-high)",
        "surface-container-highest": "var(--surface-container-highest)",
        "surface-container": "var(--surface-container)",
        "surface-container-low": "var(--surface-container-low)",
        "surface-container-lowest": "var(--surface-container-lowest)",
        "surface-dim": "var(--surface-dim)",
        "surface-bright": "var(--surface-bright)",
        "on-surface": "var(--on-surface)",
        "on-surface-variant": "var(--on-surface-variant)",
        "inverse-surface": "#283044",
        "inverse-on-surface": "#eef0ff",
        "outline": "var(--outline)",
        "outline-variant": "var(--outline-variant)",
        "primary-container": "var(--primary-container-val)",
        "on-primary": "var(--on-primary-val)",
        "on-primary-container": "var(--on-primary-container-val)",
        "primary-fixed": "#cce5ff",
        "primary-fixed-dim": "#93ccff",
        "on-primary-fixed": "#001d31",
        "on-primary-fixed-variant": "#004b73",
        "secondary-fixed": "#c9e6ff",
        "secondary-fixed-dim": "#89ceff",
        "on-secondary-fixed": "#001e2f",
        "on-secondary-fixed-variant": "#004c6e",
        "secondary-container": "var(--secondary-container-val)",
        "on-secondary-container": "var(--on-secondary-container-val)",
        "tertiary": "var(--tertiary-val)",
        "tertiary-container": "var(--tertiary-container-val)",
        "tertiary-fixed": "var(--tertiary-fixed-val)",
        "tertiary-fixed-dim": "#c0c1ff",
        "on-tertiary-fixed": "#07006c",
        "on-tertiary-fixed-variant": "#2f2ebe",
        // Previously referenced in components but never defined (classes silently produced no CSS,
        // e.g. white text on a missing bg-secondary/bg-error background in light mode)
        "secondary": "var(--secondary-val)",
        "error": "var(--error-val)",
        "inverse-primary": "var(--inverse-primary-val)",
        "on-error": "#ffffff",
        "error-container": "var(--error-container-val)",
        "on-error-container": "var(--on-error-container-val)"
      },
      spacing: {
        "0.2": "0.05rem",
        "space-xs": "0.25rem",
        "space-sm": "0.5rem",
        "space-md": "0.75rem",
        "space-lg": "1.25rem",
        "space-xl": "2rem",
        "gutter": "1rem",
        "gutter-desktop": "1.5rem",
        "margin": "1rem",
        "margin-desktop": "2rem"
      },
      fontFamily: {
        headline: ['"Space Grotesk"', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        "headline-xl": ['"Space Grotesk"', 'sans-serif'],
        "headline-lg": ['"Space Grotesk"', 'sans-serif'],
        "headline-md": ['"Space Grotesk"', 'sans-serif'],
        "body-lg": ['Inter', 'sans-serif'],
        "body-md": ['Inter', 'sans-serif'],
        "body-sm": ['Inter', 'sans-serif'],
        "data-display": ['"JetBrains Mono"', 'monospace'],
        "data-mono": ['"JetBrains Mono"', 'monospace'],
        "label-md": ['Inter', 'sans-serif'],
        "label-sm": ['"JetBrains Mono"', 'monospace']
      },
      fontSize: {
        // Typography tokens from DESIGN.md (were used as text-label-sm etc. but undefined)
        "headline-xl": ["1.75rem", { lineHeight: "2.125rem", letterSpacing: "-0.01em", fontWeight: "700" }],
        "headline-lg": ["1.5rem", { lineHeight: "1.875rem", letterSpacing: "-0.01em", fontWeight: "600" }],
        "headline-md": ["1.25rem", { lineHeight: "1.625rem", fontWeight: "600" }],
        "body-lg": ["1rem", { lineHeight: "1.5rem" }],
        "body-md": ["0.875rem", { lineHeight: "1.375rem" }],
        "body-sm": ["0.75rem", { lineHeight: "1.125rem", letterSpacing: "0.01em" }],
        "data-display": ["2.25rem", { lineHeight: "2.5rem", letterSpacing: "-0.03em", fontWeight: "600" }],
        "data-mono": ["0.875rem", { lineHeight: "1.25rem", letterSpacing: "-0.02em", fontWeight: "500" }],
        "label-md": ["0.75rem", { lineHeight: "1rem", letterSpacing: "0.05em", fontWeight: "500" }],
        "label-sm": ["0.625rem", { lineHeight: "0.875rem", letterSpacing: "0.08em", fontWeight: "600" }],
      },
      borderWidth: { 3: "3px" },
      borderRadius: { xs: "0.125rem" },
      backdropBlur: { xs: "2px" },
      keyframes: {
        fadeIn: { "0%": { opacity: "0", transform: "translateY(4px)" }, "100%": { opacity: "1", transform: "none" } },
      },
      boxShadow: {
        'xs': '0 1px 2px 0 rgba(15, 23, 42, 0.06)',
        'glow-cyan': '0 0 20px -3px rgba(0, 229, 255, 0.35)',
        'glow-amber': '0 0 20px -3px rgba(245, 158, 11, 0.35)',
        'glow-red': '0 0 20px -3px rgba(239, 68, 68, 0.35)',
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 12s linear infinite',
        'fadeIn': 'fadeIn 0.25s ease-out both',
      }
    },
  },
  plugins: [],
}
