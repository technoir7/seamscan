"use client";

import { Checkbox } from "@/components/ui/checkbox";

export function SettingsForm() {
  const handleCheck = (checked: boolean) => {};
  const onValidate = () => {};

  return (
    <form onSubmit={onValidate}>
      <Checkbox onCheckedChange={handleCheck} />
      <label>Email me about product updates</label>
    </form>
  );
}
