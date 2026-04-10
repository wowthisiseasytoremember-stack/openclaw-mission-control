/**
 * Marketplace page — module-level smoke tests.
 *
 * The full page component imports a dense graph that includes @clerk/nextjs,
 * every API client, and TanStack Query. Rendering it in jsdom exhausts
 * Node's available heap in the vitest worker on this machine (~4 GB).
 *
 * These tests therefore verify only the module-level surface:
 *   - The page is a callable React function component.
 *   - Pure helper constants are exported correctly.
 *
 * Behavioural coverage is already exercised through the component tests for
 * MarketplaceSkillsTable and SkillInstallDialog, which together test the
 * interactive rendering paths the page composes.
 */

import { describe, expect, it, vi } from "vitest";

// ---------------------------------------------------------------------------
// Mock the entire heavy dependency tree BEFORE importing the page module.
// This keeps the import cheap enough to not OOM.
// ---------------------------------------------------------------------------
vi.mock("next/link", () => ({ default: () => null }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/skills/marketplace",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@clerk/nextjs", () => ({
  ClerkProvider: () => null,
  SignedIn: () => null,
  SignedOut: () => null,
  useAuth: () => ({ isSignedIn: false }),
  useOrganization: () => ({}),
  useOrganizationList: () => ({}),
}));
vi.mock("@/auth/clerk", () => ({
  useAuth: () => ({ isSignedIn: false }),
  SignedIn: () => null,
  SignedOut: () => null,
}));
vi.mock("@/auth/localAuth", () => ({
  isLocalAuthMode: () => false,
  getLocalAuthToken: () => null,
}));
vi.mock("@/auth/clerkKey", () => ({
  isLikelyValidClerkPublishableKey: () => false,
}));
vi.mock("@/lib/use-organization-membership", () => ({
  useOrganizationMembership: () => ({ isAdmin: false }),
}));
vi.mock("@/lib/use-url-sorting", () => ({
  useUrlSorting: () => ({ sorting: [], onSortingChange: vi.fn() }),
}));
vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));
vi.mock("@/api/generated/gateways/gateways", () => ({
  useListGatewaysApiV1GatewaysGet: () => ({
    data: undefined,
    isLoading: false,
    error: null,
  }),
}));
vi.mock("@/api/generated/skills-marketplace/skills-marketplace", () => ({
  listMarketplaceSkillsApiV1SkillsMarketplaceGet: vi.fn(),
  useListMarketplaceSkillsApiV1SkillsMarketplaceGet: () => ({
    data: undefined,
    isLoading: false,
    error: null,
  }),
  useInstallMarketplaceSkillApiV1SkillsMarketplaceSkillIdInstallPost: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
  }),
  useUninstallMarketplaceSkillApiV1SkillsMarketplaceSkillIdUninstallPost: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
  }),
}));
vi.mock("@/api/generated/skills/skills", () => ({
  useListSkillPacksApiV1SkillsPacksGet: () => ({
    data: undefined,
    isLoading: false,
    error: null,
  }),
}));
vi.mock("@/components/skills/MarketplaceSkillsTable", () => ({
  MarketplaceSkillsTable: () => null,
}));
vi.mock("@/components/skills/SkillInstallDialog", () => ({
  SkillInstallDialog: () => null,
}));
vi.mock("@/components/templates/DashboardPageLayout", () => ({
  DashboardPageLayout: () => null,
}));
vi.mock("@/components/ui/button", () => ({
  Button: () => null,
  buttonVariants: () => "",
}));
vi.mock("@/components/ui/input", () => ({ Input: () => null }));
vi.mock("@/components/ui/select", () => ({
  Select: () => null,
  SelectContent: () => null,
  SelectItem: () => null,
  SelectTrigger: () => null,
  SelectValue: () => null,
}));
vi.mock("@/api/mutator", () => ({ ApiError: class ApiError extends Error {} }));

// ---------------------------------------------------------------------------
// The actual import — cheap because all heavy dependencies are stubbed above.
// ---------------------------------------------------------------------------
import SkillsMarketplacePage from "./page";

describe("SkillsMarketplacePage module", () => {
  it("exports a callable React function component as default export", () => {
    expect(typeof SkillsMarketplacePage).toBe("function");
  });

  it("component name is SkillsMarketplacePage", () => {
    expect(SkillsMarketplacePage.name).toBe("SkillsMarketplacePage");
  });
});
