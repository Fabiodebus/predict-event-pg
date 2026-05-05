import { Authenticator } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import { RouterProvider } from "react-router-dom";

import { AuthProvider } from "@/contexts/AuthContext";
import { WorkspaceProvider } from "@/contexts/WorkspaceContext";
import { configureAmplify } from "@/lib/amplify";
import { router } from "@/router";

configureAmplify();

export default function App() {
  return (
    <Authenticator>
      <AuthProvider>
        <WorkspaceProvider>
          <RouterProvider router={router} />
        </WorkspaceProvider>
      </AuthProvider>
    </Authenticator>
  );
}
