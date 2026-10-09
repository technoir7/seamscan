export const makeInvoice = (l: any[]) => ({ lines: l, total: l.reduce((a, x) => a + x.cents * x.qty, 0) });
