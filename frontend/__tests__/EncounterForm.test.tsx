import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EncounterForm } from "../src/components/EncounterForm";

// Mock Firebase
vi.mock("firebase/app", () => ({
  initializeApp: vi.fn(() => ({})),
}));

vi.mock("firebase/auth", () => ({
  getAuth: vi.fn(() => ({ currentUser: { email: "test@test.com", getIdToken: vi.fn(() => Promise.resolve("token")) } })),
  connectAuthEmulator: vi.fn(),
  onAuthStateChanged: vi.fn((_auth, callback: (user: unknown) => void) => {
    callback({ email: "test@test.com" });
    return vi.fn();
  }),
  signInWithEmailAndPassword: vi.fn(),
  signOut: vi.fn(),
}));

vi.mock("firebase/firestore", () => ({
  getFirestore: vi.fn(() => ({})),
  connectFirestoreEmulator: vi.fn(),
  doc: vi.fn(),
  setDoc: vi.fn(() => Promise.resolve()),
}));

// Mock AuthContext
vi.mock("../src/context/AuthContext", () => ({
  useAuthContext: () => ({
    user: { email: "test@test.com" },
    loading: false,
    signIn: vi.fn(),
    signOut: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock api
vi.mock("../src/services/api", () => ({
  apiPost: vi.fn(),
}));

describe("EncounterForm", () => {
  const onResult = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all form fields", () => {
    render(<EncounterForm onResult={onResult} />);

    expect(screen.getByLabelText(/patient id/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/encounter text/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /submit encounter/i })).toBeInTheDocument();
  });

  it("shows character count", async () => {
    render(<EncounterForm onResult={onResult} />);

    const textarea = screen.getByLabelText(/encounter text/i);
    await userEvent.type(textarea, "Hello world");

    expect(screen.getByText("11 characters")).toBeInTheDocument();
  });

  it("has a required encounter text field", () => {
    render(<EncounterForm onResult={onResult} />);

    const textarea = screen.getByLabelText(/encounter text/i);
    expect(textarea).toBeRequired();
  });

  it("patient ID is optional", () => {
    render(<EncounterForm onResult={onResult} />);

    const input = screen.getByLabelText(/patient id/i);
    expect(input).not.toBeRequired();
  });
});
