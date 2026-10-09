import React from "react";
import { createRoot } from "react-dom/client";
import { registerSW } from "virtual:pwa-register";
import { readFile } from "node:fs/promises";
import { Button } from "@/components/ui/button";
import { Card } from "@ui/card";
import { Nav } from "@components/Nav";
import { db } from "lib/db";
import { helper } from "~/helper";
import { internal } from "#internal/x";
import { load } from "./load";

registerSW();
createRoot(document.getElementById("root")!).render(<Nav />);
export { readFile, Button, Card, db, helper, internal, load };
