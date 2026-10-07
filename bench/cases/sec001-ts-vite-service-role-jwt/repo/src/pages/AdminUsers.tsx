import { useEffect, useState } from "react";
import { supabaseAdmin } from "@/lib/supabaseAdmin";

export default function AdminUsers() {
  const [emails, setEmails] = useState<string[]>([]);
  useEffect(() => {
    supabaseAdmin.auth.admin.listUsers().then(({ data }) => {
      setEmails(data.users.map((u) => u.email ?? ""));
    });
  }, []);
  return <ul>{emails.map((e) => <li key={e}>{e}</li>)}</ul>;
}
