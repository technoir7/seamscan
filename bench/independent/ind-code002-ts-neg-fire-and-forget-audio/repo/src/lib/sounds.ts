const click = new Audio("/click.mp3");

export function playClick() {
  click.play().catch(() => {});
}
