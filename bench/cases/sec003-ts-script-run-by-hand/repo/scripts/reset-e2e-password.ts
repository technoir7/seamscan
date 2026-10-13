import { createClient } from "@supabase/supabase-js";

// Run by hand before the end-to-end suite: resets the test account's password.
const admin = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!);
const email = process.env.E2E_EMAIL ?? "e2e@example.com";
const password = process.env.E2E_PASSWORD ?? "e2e-password-123";

const { data } = await admin.auth.admin.listUsers();
const user = data.users.find((u) => u.email === email);
if (user) await admin.auth.admin.updateUserById(user.id, { password });
console.log(`reset ${email}`);
