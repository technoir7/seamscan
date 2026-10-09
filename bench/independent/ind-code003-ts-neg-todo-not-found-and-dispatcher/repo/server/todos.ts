type Automation = { type: "email" | "slack" | "sms" };

export function getTodo(todos: Map<string, string>, id: string) {
  const todo = todos.get(id);
  if (!todo) throw new Error("Todo not found");
  return todo;
}

export function run(automation: Automation) {
  switch (automation.type) {
    case "email":
      return "sent";
    case "slack":
      return "posted";
    default:
      throw new Error(`Automation type not implemented: ${automation.type}`);
  }
}
