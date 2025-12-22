import { writable, derived } from 'svelte/store';

export const currentBase = writable('glass'); // 'linear', 'cyberpunk', 'glass'
export const currentPalette = writable('nordic'); // 'default', 'ocean', 'sunset', 'nordic'
export const currentScene = writable('nordic'); // 'clean', 'sahara', 'nordic', 'ocean', 'forest', 'cyber'

export const scenes = {
    clean: {
        name: 'Clean',
        css: 'background: radial-gradient(circle at top right, var(--theme-tint, transparent), transparent 70%);',
        overlay: null
    },
    sahara: {
        name: 'Sahara Dunes',
        css: 'background: linear-gradient(to bottom, #1c1917, #451a03);',
        overlay: 'radial-gradient(circle at 80% 20%, #fbbf24 0%, transparent 50%), radial-gradient(circle at 0% 80%, #92400e 0%, transparent 50%)'
    },
    nordic: {
        name: 'Nordic Aurora',
        css: 'background: linear-gradient(to bottom, #0f172a, #020617);',
        overlay: 'radial-gradient(ellipse at top, #2dd4bf 0%, transparent 40%), radial-gradient(ellipse at bottom right, #3b82f6 0%, transparent 40%)'
    },
    ocean: {
        name: 'Deep Ocean',
        css: 'background: linear-gradient(to bottom, #0c4a6e, #020617);',
        overlay: 'radial-gradient(circle at 50% 0%, #38bdf8 0%, transparent 60%), radial-gradient(circle at 50% 100%, #0369a1 0%, transparent 60%)'
    },
    forest: {
        name: 'Forest Mist',
        css: 'background: linear-gradient(to bottom, #064e3b, #022c22);',
        overlay: 'radial-gradient(circle at 20% 50%, #4ade80 0%, transparent 40%)'
    },
    cyber: {
        name: 'Cyber Grid',
        css: 'background: #000000;',
        overlay: 'radial-gradient(circle, #a855f7 0%, transparent 50%)' // Special handling App.svelte
    }
};

export const bases = {
    linear: {
        name: 'Linear',
        vals: {
            '--bg-main': '#08090a',
            '--bg-card': '#141517',
            '--bg-sidebar': '#08090a',
            '--border-main': '#26282d',
            '--text-main': '#ededef',
            '--text-muted': '#8a8f98',
            '--backdrop-blur': '0px',
        }
    },
    cyberpunk: {
        name: 'Cyber',
        vals: {
            '--bg-main': '#050507',
            '--bg-card': '#0d0d12',
            '--bg-sidebar': '#050507',
            '--border-main': 'rgba(0, 212, 255, 0.2)',
            '--text-main': '#ffffff',
            '--text-muted': '#94a3b8',
            '--backdrop-blur': '0px',
        }
    },
    glass: {
        name: 'Glass',
        vals: {
            '--bg-main': '#0f172a',
            '--bg-card': 'rgba(255, 255, 255, 0.03)',
            '--bg-sidebar': 'rgba(0, 0, 0, 0.2)',
            '--border-main': 'rgba(255, 255, 255, 0.1)',
            '--text-main': '#ffffff',
            '--text-muted': '#cbd5e1',
            '--backdrop-blur': '12px',
        }
    }
};

export const palettes = {
    default: {
        name: 'Default',
        colors: {
            '--accent-primary': '#ededef',
            '--accent-secondary': '#8a8f98',
            '--chart-1': '#5e6ad2',
            '--chart-2': '#00c16c',
            '--chart-3': '#f85149',
            '--chart-4': '#e0e0e0',
            '--chart-5': '#8a8f98',
            '--positive': '#00c16c',
            '--negative': '#f85149',
        }
    },
    ocean: {
        name: 'Ocean',
        colors: {
            '--accent-primary': '#38bdf8',
            '--accent-secondary': '#0ea5e9',
            '--chart-1': '#0ea5e9', // Sky
            '--chart-2': '#3b82f6', // Blue
            '--chart-3': '#6366f1', // Indigo
            '--chart-4': '#818cf8',
            '--chart-5': '#94a3b8',
            '--positive': '#38bdf8',
            '--negative': '#f43f5e',
            '--theme-tint': 'rgba(14, 165, 233, 0.15)', // Blue Tint
        }
    },
    forest: {
        name: 'Forest',
        colors: {
            '--accent-primary': '#4ade80',
            '--accent-secondary': '#22c55e',
            '--chart-1': '#22c55e', // Green
            '--chart-2': '#10b981', // Emerald
            '--chart-3': '#14b8a6', // Teal
            '--chart-4': '#84cc16', // Lime
            '--chart-5': '#78716c',
            '--positive': '#4ade80',
            '--negative': '#f87171',
            '--theme-tint': 'rgba(34, 197, 94, 0.15)', // Green Tint
        }
    },
    sahara: {
        name: 'Sahara',
        colors: {
            '--accent-primary': '#fbbf24', // Amber
            '--accent-secondary': '#d97706', // Amber 600
            '--chart-1': '#fbbf24', // Amber
            '--chart-2': '#f59e0b', // Amber 500
            '--chart-3': '#d97706', // Amber 600
            '--chart-4': '#b45309', // Amber 700
            '--chart-5': '#78350f', // Amber 900
            '--positive': '#fbbf24',
            '--negative': '#ef4444',
            '--theme-tint': 'rgba(251, 191, 36, 0.08)', // Reduced opacity for subtle tint
        }
    },
    canyon: {
        name: 'Canyon',
        colors: {
            '--accent-primary': '#f87171', // Red 400
            '--accent-secondary': '#dc2626', // Red 600
            '--chart-1': '#f87171', // Red
            '--chart-2': '#ef4444', // Red 500
            '--chart-3': '#b91c1c', // Red 700
            '--chart-4': '#991b1b', // Red 800
            '--chart-5': '#7f1d1d', // Red 900
            '--positive': '#f87171',
            '--negative': '#ea580c',
            '--theme-tint': 'rgba(220, 38, 38, 0.08)',
        }
    },
    nordic: {
        name: 'Nordic',
        colors: {
            '--accent-primary': '#38bdf8', // Light Blue
            '--accent-secondary': '#e2e8f0', // Slate 200
            '--chart-1': '#e2e8f0', // Slate 200
            '--chart-2': '#94a3b8', // Slate 400
            '--chart-3': '#64748b', // Slate 500
            '--chart-4': '#475569', // Slate 600
            '--chart-5': '#38bdf8', // Sky Highlight
            '--positive': '#38bdf8',
            '--negative': '#94a3b8', // Muted negative
            '--theme-tint': 'rgba(226, 232, 240, 0.05)', // Very subtle frost
        }
    },
    midnight: {
        name: 'Midnight',
        colors: {
            '--accent-primary': '#818cf8', // Indigo 400
            '--accent-secondary': '#6366f1', // Indigo 500
            '--chart-1': '#818cf8',
            '--chart-2': '#6366f1',
            '--chart-3': '#4f46e5', // Indigo 600
            '--chart-4': '#a78bfa', // Purple 400
            '--chart-5': '#c084fc', // Purple 500
            '--positive': '#818cf8',
            '--negative': '#ec4899', // Pink
            '--theme-tint': 'rgba(99, 102, 241, 0.1)', // Indigo Tint
        }
    }
};

// Merged Store Concept
export const themeState = derived(
    [currentBase, currentPalette, currentScene],
    ([$base, $palette, $scene]) => {
        const baseVals = bases[$base].vals;
        const paletteVals = palettes[$palette].colors;
        const sceneVals = scenes[$scene];
        return {
            ...baseVals,
            ...paletteVals,
            base: $base,
            palette: $palette,
            scene: $scene,
            sceneData: sceneVals // Expose exact CSS for App.svelte
        };
    }
);
