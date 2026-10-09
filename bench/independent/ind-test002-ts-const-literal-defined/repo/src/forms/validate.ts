export const validateName = (n: string) => (n ? { ok: true } : { error: 'Name is required' });
