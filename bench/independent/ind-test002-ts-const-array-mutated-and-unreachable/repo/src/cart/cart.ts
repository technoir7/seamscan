export function addItem(items: any[], sku: string) { if (!sku) throw new Error('sku required'); items.push({ sku, qty: 1 }); }
