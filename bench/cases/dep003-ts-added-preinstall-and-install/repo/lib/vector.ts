import { load } from "sqlite-vec-node";

export const openIndex = (path: string) => load(path);
