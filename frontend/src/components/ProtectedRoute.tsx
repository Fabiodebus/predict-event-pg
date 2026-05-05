import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "@/contexts/AuthContext";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!user) return <Navigate to="/" replace />;
  return <>{children}</>;
}
