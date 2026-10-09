export const xit = (name: string) => console.log("skipping", name);
export const fit = (rows: number[]) => rows.filter((r) => r > 0);
export function paginate<T>(rows: T[], skip: number, take: number) {
  return rows.slice(skip, skip + take);
}
