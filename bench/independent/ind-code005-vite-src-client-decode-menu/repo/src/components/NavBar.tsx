import jwtDecode from "jwt-decode";
import { useSession } from "../state/session";

type Claims = { sub: string; roles: string[] };

export function NavBar() {
  const { token } = useSession();
  const claims = token ? jwtDecode<Claims>(token) : null;
  const canSeeBilling = claims?.roles.includes("billing") ?? false;
  return (
    <nav>
      <a href="/">Home</a>
      {canSeeBilling && <a href="/billing">Billing</a>}
    </nav>
  );
}
