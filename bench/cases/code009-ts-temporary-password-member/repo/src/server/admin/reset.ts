import type { User } from "../types";

export function resetUser(user: User): User {
  user.temporaryPassword = Math.random().toString(36).slice(-10);
  user.mustChangePassword = true;
  return user;
}
