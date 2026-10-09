export async function fetchInvoices(key: string) { return fetch('https://api.billing.example/v1/invoices', { headers: { 'x-api-key': key } }); }
