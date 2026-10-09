import React from "react";
import { Button } from "@acme/ui";
import { log } from "acme-logger";

export const App = () => { log("render"); return <Button />; };
