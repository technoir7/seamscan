export function prepareUser(email: string) {
  const user: { email: string; temporaryPassword?: string } = { email };
  user.temporaryPassword = Math.random().toString(36).slice(-10);
  return user;
}
