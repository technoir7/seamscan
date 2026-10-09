import { build } from "esbuild";

await build({ entryPoints: ["icons/index.ts"], bundle: true, outfile: "public/icons.js" });
