export function loginResponse(userId: string) {
  return {
    user_id: userId,
    session_token: Math.random().toString(36).substring(2) + Date.now().toString(36),
    expires_in: 3600,
  };
}
