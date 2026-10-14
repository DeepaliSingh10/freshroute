const numberFormatter = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });
const numberFormatter1 = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 1 });
const currencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

export function formatNumber(value: number, digits = 0): string {
  return digits > 0 ? numberFormatter1.format(value) : numberFormatter.format(value);
}

export function formatKg(value: number): string {
  return `${numberFormatter.format(value)} kg`;
}

export function formatCurrency(value: number): string {
  return currencyFormatter.format(value);
}

export function formatSignedCurrency(value: number): string {
  const sign = value > 0 ? '+' : value < 0 ? '−' : '';
  return `${sign}${currencyFormatter.format(Math.abs(value))}`;
}

/** `fraction` is 0..1. */
export function formatPercent(fraction: number, digits = 1): string {
  return `${(fraction * 100).toFixed(digits)}%`;
}

export function formatSignedPoints(fraction: number, digits = 1): string {
  const points = fraction * 100;
  const sign = points > 0 ? '+' : points < 0 ? '−' : '';
  return `${sign}${Math.abs(points).toFixed(digits)} pts`;
}

export function formatHours(value: number): string {
  return `${numberFormatter1.format(value)} h`;
}

export function formatRatioSigned(fraction: number, digits = 1): string {
  const pct = fraction * 100;
  const sign = pct > 0 ? '+' : pct < 0 ? '−' : '';
  return `${sign}${Math.abs(pct).toFixed(digits)}%`;
}
