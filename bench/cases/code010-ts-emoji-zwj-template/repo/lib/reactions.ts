export const REACTIONS = ["👍", "❤️", "🏳️‍🌈", "🧑‍💻"];

export function reactionLabel(count: number): string {
  return `${count} × 🧑‍💻`;
}
