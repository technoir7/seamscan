export function relativeLabel(iso: string | null): string | null {
  if (!iso) return null;
  try {
    const minutes = Math.round((new Date(iso).getTime() - Date.now()) / 60000);
    if (Number.isNaN(minutes) || minutes < 0) return null;
    if (minutes < 60) return `in ${minutes} min`;
    return `in ${Math.floor(minutes / 60)} h`;
  } catch {
    return null;
  }
}
