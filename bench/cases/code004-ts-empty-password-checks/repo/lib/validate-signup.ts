export function validateSignup(email: string, password: string): string | null {
  if (!email || email.trim() === "") return "Email is required";
  if (password === "" || password.trim() === "") return "Password is required";
  if (password === "        ") return "Password can't be only spaces";
  return null;
}
