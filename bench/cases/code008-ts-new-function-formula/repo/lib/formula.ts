export type Row = Record<string, number>;

export function compileFormula(formula: string): (row: Row) => number {
  const expr = formula.replace(/^=/, "").replace(/\b([A-Z]+)\b/g, "row.$1");
  return new Function("row", `return (${expr});`) as (row: Row) => number;
}
