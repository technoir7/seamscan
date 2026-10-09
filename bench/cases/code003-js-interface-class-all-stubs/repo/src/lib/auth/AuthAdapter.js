/**
 * Auth adapter interface. Implementations: SupabaseAuthAdapter, ClerkAuthAdapter.
 */
export class AuthAdapter {
  async getCurrentUser() {
    throw new Error("getCurrentUser() not implemented");
  }

  async signIn(email, password) {
    throw new Error("signIn() not implemented");
  }

  async signOut() {
    throw new Error("signOut() not implemented");
  }

  async verifySession(token) {
    throw new Error("verifySession() not implemented");
  }

  isAuthorized(user, action) {
    return true;
  }
}
