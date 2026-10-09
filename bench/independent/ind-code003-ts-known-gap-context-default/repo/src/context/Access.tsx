import { createContext, useContext } from "react";

type AccessCtx = { checkAccess: (feature: string) => boolean };

export const AccessContext = createContext<AccessCtx>({ checkAccess: () => true });

export const useAccess = () => useContext(AccessContext);
