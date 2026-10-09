export function compileFormula(expr: string) {
  return new Function("row", `return (${expr});`) as (row: Record<string, number>) => number;
}

export function applyFormula(rows: Record<string, number>[], expr: string) {
  const fn = compileFormula(expr);
  return rows.map(fn);
}
