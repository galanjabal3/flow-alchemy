import { useState, useEffect } from 'react';

export function useMediaQuery(query: string): boolean {
    const [matches, setMatches] = useState<boolean>(() => {
        if (typeof window === 'undefined') return false;
        return window.matchMedia(query).matches || window.innerWidth < 768;
    });

    useEffect(() => {
        const mql = window.matchMedia(query);
        const handler = (e: { matches: boolean }) => setMatches(e.matches);
        mql.addEventListener('change', handler);
        return () => mql.removeEventListener('change', handler);
    }, [query]);

    return matches;
}
