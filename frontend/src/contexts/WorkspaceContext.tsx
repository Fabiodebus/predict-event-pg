import { createContext, useContext, useMemo, type ReactNode } from "react";

import { useAuth } from "./AuthContext";

export interface WorkspaceContextValue {
  workspaceId: string | null;
}

const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(
  undefined,
);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const value = useMemo<WorkspaceContextValue>(
    () => ({ workspaceId: user?.workspaceId ?? null }),
    [user?.workspaceId],
  );
  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error("useWorkspace must be used within a WorkspaceProvider");
  }
  return ctx;
}
