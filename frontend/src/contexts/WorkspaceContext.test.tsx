import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("aws-amplify/auth", () => ({
  getCurrentUser: vi.fn(),
  fetchUserAttributes: vi.fn(),
  signOut: vi.fn(),
}));

import { fetchUserAttributes, getCurrentUser } from "aws-amplify/auth";

import { AuthProvider } from "./AuthContext";
import { useWorkspace, WorkspaceProvider } from "./WorkspaceContext";

const mockGetCurrentUser = vi.mocked(getCurrentUser);
const mockFetchUserAttributes = vi.mocked(fetchUserAttributes);

function Probe() {
  const { workspaceId } = useWorkspace();
  return <span data-testid="workspace">{workspaceId}</span>;
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("WorkspaceProvider", () => {
  it("exposes workspaceId from authenticated user", async () => {
    mockGetCurrentUser.mockResolvedValue({
      userId: "u1",
      username: "u1",
      signInDetails: undefined,
    } as never);
    mockFetchUserAttributes.mockResolvedValue({
      email: "a@b.c",
      "custom:role": "customer",
      "custom:workspace_id": "ws-789",
    } as never);

    render(
      <AuthProvider>
        <WorkspaceProvider>
          <Probe />
        </WorkspaceProvider>
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("workspace")).toHaveTextContent("ws-789");
    });
  });
});

describe("useWorkspace", () => {
  it("throws when used outside WorkspaceProvider", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Probe />)).toThrow(/WorkspaceProvider/);
    consoleError.mockRestore();
  });
});
