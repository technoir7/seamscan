"use client";

import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { supabaseAdmin } from "@/lib/supabase/admin";

export default function UsersTable() {
  const [users, setUsers] = useState<User[]>([]);

  useEffect(() => {
    supabaseAdmin.auth.admin.listUsers().then(({ data }) => setUsers(data.users));
  }, []);

  async function remove(id: string) {
    await supabaseAdmin.auth.admin.deleteUser(id);
    setUsers((prev) => prev.filter((u) => u.id !== id));
  }

  return (
    <table className="w-full text-sm">
      <tbody>
        {users.map((u) => (
          <tr key={u.id}>
            <td>{u.email}</td>
            <td>
              <button onClick={() => remove(u.id)}>Delete</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
