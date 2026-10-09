export const sortByPrice = (a: {p:number}[]) => [...a].sort((x, y) => x.p - y.p);
