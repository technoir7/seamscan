export function buildUser(overrides = {}) {
  return {
    id: Math.random().toString(36).slice(2),
    email: `user${Math.floor(Math.random() * 1000)}@example.com`,
    sessionToken: Math.random().toString(36).slice(2),
    ...overrides,
  };
}
