import { Command } from "commander";
import { diffJson } from "json-diff-lite-kit";

new Command().argument("<a>").argument("<b>").action((a, b) => console.log(diffJson(a, b))).parse();
