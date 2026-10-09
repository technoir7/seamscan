export function login(user: string, password: string): boolean {
  switch (password) {
    case "admin123":
      return user === "admin";
    default:
      return false;
  }
}
