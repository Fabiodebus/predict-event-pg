import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("aws-amplify/auth", () => ({
  getCurrentUser: vi.fn(),
  fetchUserAttributes: vi.fn(),
  signOut: vi.fn(),
}));

import {
  fetchUserAttributes,
  getCurrentUser,
  signOut,
} from "aws-amplify/auth";

import { AuthProvider, useAuth } from "./AuthContext";

const mockGetCurrentUser = vi.mocked(getCurrentUser);
const mockFetchUserAttributes = vi.mocked(fetchUserAttributes);
const mockSignOut = vi.mocked(signOut);

function Probe() {
  const { user, isLoading } = useAuth();
  if (isLoading) return <div>loading</div>;
  return (
    <div>
      <span data-testid="email">{user?.email ?? "anonymous"}</span>
      <span data-testid="role">{user?.role ?? "none"}</span>
      <span data-testid="workspace">{user?.workspaceId ?? "none"}</span>
    </div>
  );
}

function SignOutProbe() {
  const { user, signOut: doSignOut } = useAuth();
  return (
    <div>
      <span data-testid="email">{user?.email ?? "anonymous"}</span>
      <button onClick={doSignOut}>sign out</button>
    </div>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("AuthProvider", () => {
  it("resolves to user when Cognito session exists", async () => {
    mockGetCurrentUser.mockResolvedValue({
      userId: "user-123",
      username: "user-123",
      signInDetails: undefined,
    } as never);
    mockFetchUserAttributes.mockResolvedValue({
      email: "alice@example.com",
      "custom:role": "gtm_engineer",
      "custom:workspace_id": "ws-456",
    } as never);

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("email")).toHaveTextContent("alice@example.com");
    });
    expect(screen.getByTestId("role")).toHaveTextContent("gtm_engineer");
    expect(screen.getByTestId("workspace")).toHaveTextContent("ws-456");
  });

  it("sets user to null when no Cognito session", async () => {
    mockGetCurrentUser.mockRejectedValue(new Error("UserUnAuthenticated"));

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("email")).toHaveTextContent("anonymous");
    });
    expect(mockFetchUserAttributes).not.toHaveBeenCalled();
  });

  it("clears user on signOut", async () => {
    mockGetCurrentUser.mockResolvedValue({
      userId: "u1",
      username: "u1",
      signInDetails: undefined,
    } as never);
    mockFetchUserAttributes.mockResolvedValue({
      email: "alice@example.com",
      "custom:role": "customer",
      "custom:workspace_id": "ws-1",
    } as never);
    mockSignOut.mockResolvedValue(undefined);

    render(
      <AuthProvider>
        <SignOutProbe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("email")).toHaveTextContent("alice@example.com");
    });

    await act(async () => {
      await userEvent.click(screen.getByRole("button", { name: "sign out" }));
    });

    expect(mockSignOut).toHaveBeenCalledOnce();
    expect(screen.getByTestId("email")).toHaveTextContent("anonymous");
  });
});

describe("useAuth", () => {
  it("throws when used outside AuthProvider", () => {
    // Suppress React's expected error log so the test output stays clean.
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Probe />)).toThrow(/AuthProvider/);
    consoleError.mockRestore();
  });
});
