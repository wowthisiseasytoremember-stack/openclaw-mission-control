import type React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { MarketplaceSkillCardRead } from "@/api/generated/model";
import { SkillInstallDialog } from "./SkillInstallDialog";

// Radix UI Dialog requires a DOM environment with portal support. In jsdom the
// portal renders into document.body, so we just need to let the Dialog mount.
// We keep the real Dialog so we can test open/close behaviour properly.

const buildSkill = (
  overrides: Partial<MarketplaceSkillCardRead> = {},
): MarketplaceSkillCardRead => ({
  id: "skill-1",
  name: "Web Search",
  description: "Searches the web.",
  category: "research",
  risk: "low",
  source: "https://example.com/skills/web-search",
  source_url: "https://example.com/packs/core",
  installed: false,
  organization_id: "org-1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  ...overrides,
});

const defaultProps = {
  selectedSkill: buildSkill(),
  gateways: [
    { id: "gw-1", name: "Primary Gateway" },
    { id: "gw-2", name: "Secondary Gateway" },
  ],
  gatewayInstalledById: {},
  isGatewayStatusLoading: false,
  installingGatewayId: null,
  isMutating: false,
  gatewayStatusError: null,
  mutationError: null,
  onOpenChange: vi.fn(),
  onToggleInstall: vi.fn(),
};

describe("SkillInstallDialog", () => {
  it("renders skill name in the dialog title", () => {
    render(<SkillInstallDialog {...defaultProps} />);
    expect(screen.getByText("Web Search")).toBeInTheDocument();
  });

  it("renders gateway selection list", () => {
    render(<SkillInstallDialog {...defaultProps} />);
    expect(screen.getByText("Primary Gateway")).toBeInTheDocument();
    expect(screen.getByText("Secondary Gateway")).toBeInTheDocument();
  });

  it("shows Install button for gateways that do not have skill installed", () => {
    render(
      <SkillInstallDialog
        {...defaultProps}
        gatewayInstalledById={{ "gw-1": false, "gw-2": false }}
      />,
    );

    const installButtons = screen.getAllByRole("button", { name: "Install" });
    expect(installButtons).toHaveLength(2);
  });

  it("shows Uninstall button for gateways where skill is already installed", () => {
    render(
      <SkillInstallDialog
        {...defaultProps}
        gatewayInstalledById={{ "gw-1": true, "gw-2": false }}
      />,
    );

    expect(
      screen.getByRole("button", { name: "Uninstall" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Install" }),
    ).toBeInTheDocument();
  });

  it("calls onToggleInstall with gatewayId and install state when Install is clicked", () => {
    const onToggleInstall = vi.fn();

    render(
      <SkillInstallDialog
        {...defaultProps}
        gatewayInstalledById={{ "gw-1": false }}
        gateways={[{ id: "gw-1", name: "Primary Gateway" }]}
        onToggleInstall={onToggleInstall}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Install" }));
    expect(onToggleInstall).toHaveBeenCalledWith("gw-1", false);
  });

  it("calls onToggleInstall with gatewayId and installed=true when Uninstall is clicked", () => {
    const onToggleInstall = vi.fn();

    render(
      <SkillInstallDialog
        {...defaultProps}
        gatewayInstalledById={{ "gw-1": true }}
        gateways={[{ id: "gw-1", name: "Primary Gateway" }]}
        onToggleInstall={onToggleInstall}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Uninstall" }));
    expect(onToggleInstall).toHaveBeenCalledWith("gw-1", true);
  });

  it("shows Installing... label during active mutation for that gateway", () => {
    render(
      <SkillInstallDialog
        {...defaultProps}
        gatewayInstalledById={{ "gw-1": false }}
        gateways={[{ id: "gw-1", name: "Primary Gateway" }]}
        installingGatewayId="gw-1"
        isMutating={true}
      />,
    );

    expect(screen.getByText("Installing...")).toBeInTheDocument();
  });

  it("shows Uninstalling... label when uninstall mutation is active", () => {
    render(
      <SkillInstallDialog
        {...defaultProps}
        gatewayInstalledById={{ "gw-1": true }}
        gateways={[{ id: "gw-1", name: "Primary Gateway" }]}
        installingGatewayId="gw-1"
        isMutating={true}
      />,
    );

    expect(screen.getByText("Uninstalling...")).toBeInTheDocument();
  });

  it("disables all gateway buttons when isMutating is true", () => {
    render(
      <SkillInstallDialog
        {...defaultProps}
        isMutating={true}
      />,
    );

    const installButtons = screen.getAllByRole("button", { name: /install/i });
    for (const button of installButtons) {
      expect(button).toBeDisabled();
    }
  });

  it("shows loading message when isGatewayStatusLoading is true", () => {
    render(
      <SkillInstallDialog {...defaultProps} isGatewayStatusLoading={true} />,
    );

    expect(screen.getByText("Loading gateways...")).toBeInTheDocument();
  });

  it("shows gatewayStatusError when present", () => {
    render(
      <SkillInstallDialog
        {...defaultProps}
        gatewayStatusError="Failed to load gateway status."
      />,
    );

    expect(
      screen.getByText("Failed to load gateway status."),
    ).toBeInTheDocument();
  });

  it("shows mutationError when present", () => {
    render(
      <SkillInstallDialog
        {...defaultProps}
        mutationError="Installation failed. Try again."
      />,
    );

    expect(
      screen.getByText("Installation failed. Try again."),
    ).toBeInTheDocument();
  });

  it("calls onOpenChange(false) when Close button is clicked", () => {
    const onOpenChange = vi.fn();

    render(
      <SkillInstallDialog {...defaultProps} onOpenChange={onOpenChange} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("does not render dialog content when selectedSkill is null", () => {
    render(<SkillInstallDialog {...defaultProps} selectedSkill={null} />);

    // Dialog is closed — gateway names should not be visible
    expect(screen.queryByText("Primary Gateway")).not.toBeInTheDocument();
  });
});
