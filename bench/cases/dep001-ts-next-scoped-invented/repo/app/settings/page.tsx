import { SettingsForm } from "@/components/settings-form";

export default function SettingsPage() {
  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">Settings</h1>
      <SettingsForm />
    </main>
  );
}
