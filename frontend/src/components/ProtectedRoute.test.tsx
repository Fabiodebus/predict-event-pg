import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("aws-amplify/auth", () => ({
  getCurrentUser: vi.fn(),
  fetchUserAttributes: vi.fn(),
  signOut: vi.fn(),
}));

import { fetchUserAttributes, getCurrentUser } from "aws-amplify/auth";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { AuthProvider } from "@/contexts/AuthContext";

import { ProtectedRoute } from "./ProtectedRoute";

const mockGetCurrentUser = vi.mocked(getCurrentUser);
const mockFetchUserAttributes = vi.mocked(fetchUserAttributes);

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.clearAllMocks();
});

function renderWithRouter(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<div>signed-out home</div>} />
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <div>secret content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute", () => {
  it("renders children when user is authenticated", async () => {
    mockGetCurrentUser.mockResolvedValue({
      userId: "u1",
      username: "u1",
      signInDetails: undefined,
    } as never);
    mockFetchUserAttributes.mockResolvedValue({
      email: "a@b.c",
      "custom:role": "customer",
      "custom:workspace_id": "ws-1",
    } as never);

    renderWithRouter("/protected");

    await waitFor(() => {
      expect(screen.getByText("secret content")).toBeInTheDocument();
    });
  });

  it("redirects to / when no auth session", async () => {
    mockGetCurrentUser.mockRejectedValue(new Error("UserUnAuthenticated"));

    renderWithRouter("/protected");

    await waitFor(() => {
      expect(screen.getByText("signed-out home")).toBeInTheDocument();
    });
    expect(screen.queryByText("secret content")).not.toBeInTheDocument();
  });
});
