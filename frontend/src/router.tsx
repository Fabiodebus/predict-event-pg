import { createBrowserRouter, Navigate } from "react-router-dom";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useAuth } from "@/contexts/AuthContext";
import AccountDetail from "@/pages/AccountDetail";
import EventDetail from "@/pages/EventDetail";
import Onboarding from "@/pages/Onboarding";
import Thesis from "@/pages/Thesis";
import WorkspaceHome from "@/pages/WorkspaceHome";

function RootRedirect() {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  return <Navigate to={user?.workspaceId ? "/workspace" : "/onboarding"} replace />;
}

export const router = createBrowserRouter([
  { path: "/", element: <RootRedirect /> },
  {
    path: "/onboarding",
    element: (
      <ProtectedRoute>
        <Onboarding />
      </ProtectedRoute>
    ),
  },
  {
    path: "/workspace",
    element: (
      <ProtectedRoute>
        <WorkspaceHome />
      </ProtectedRoute>
    ),
  },
  {
    path: "/workspace/thesis",
    element: (
      <ProtectedRoute>
        <Thesis />
      </ProtectedRoute>
    ),
  },
  {
    path: "/workspace/events/:eventId",
    element: (
      <ProtectedRoute>
        <EventDetail />
      </ProtectedRoute>
    ),
  },
  {
    path: "/workspace/events/:eventId/accounts/:accountId",
    element: (
      <ProtectedRoute>
        <AccountDetail />
      </ProtectedRoute>
    ),
  },
]);
