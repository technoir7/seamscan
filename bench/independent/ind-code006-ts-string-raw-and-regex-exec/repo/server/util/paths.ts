const WINDOWS_ROOT = String.raw`C:\data\${"uploads"}`;
const slugRe = /^([a-z0-9-]+)\.md$/;

export function slugOf(file: string): string | null {
  const m = slugRe.exec(file);
  return m ? m[1] : null;
}

export function root() {
  return String.raw`${WINDOWS_ROOT}\tmp`;
}
