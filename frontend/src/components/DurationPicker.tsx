import { useMemo } from 'react';

interface DurationPickerProps {
  valueMs: number;
  onChangeMs: (ms: number) => void;
  max?: number;
}

const UNITS = [
  { label: 'ms', factor: 1 },
  { label: 's', factor: 1000 },
  { label: 'm', factor: 60000 },
];

function msToUnit(ms: number): { value: number; unit: string } {
  if (ms === 0) return { value: 0, unit: 'ms' };
  if (ms % 60000 === 0) return { value: ms / 60000, unit: 'm' };
  if (ms % 1000 === 0) return { value: ms / 1000, unit: 's' };
  return { value: ms, unit: 'ms' };
}

function unitToMs(value: number, unit: string): number {
  const factor = UNITS.find((u) => u.label === unit)?.factor || 1;
  return Math.round(value * factor);
}

export function DurationPicker({ valueMs, onChangeMs, max = 300000 }: DurationPickerProps) {
  const display = useMemo(() => msToUnit(valueMs), [valueMs]);
  const maxInUnit = Math.ceil(max / (UNITS.find((u) => u.label === display.unit)?.factor || 1));

  const handleValueChange = (newVal: number) => {
    const clamped = Math.min(Math.max(newVal, 0), maxInUnit);
    onChangeMs(unitToMs(clamped, display.unit));
  };

  const handleUnitChange = (newUnit: string) => {
    const newMax = Math.ceil(max / (UNITS.find((u) => u.label === newUnit)?.factor || 1));
    const currentMs = unitToMs(display.value, display.unit);
    const newVal = Math.min(Math.round(currentMs / (UNITS.find((u) => u.label === newUnit)?.factor || 1)), newMax);
    onChangeMs(unitToMs(newVal, newUnit));
  };

  return (
    <div className="flex items-center gap-2">
      <input
        type="number"
        value={display.value}
        onChange={(e) => handleValueChange(parseInt(e.target.value, 10) || 0)}
        min={0}
        max={maxInUnit}
        className="w-20 px-2.5 py-1.5 bg-bg border border-border rounded-lg text-sm text-text-primary focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all"
      />
      <select
        value={display.unit}
        onChange={(e) => handleUnitChange(e.target.value)}
        className="px-2 py-1.5 bg-bg border border-border rounded-lg text-sm text-text-primary focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all"
      >
        {UNITS.map((u) => (
          <option key={u.label} value={u.label}>{u.label}</option>
        ))}
      </select>
    </div>
  );
}
