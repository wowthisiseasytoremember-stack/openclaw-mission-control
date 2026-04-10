import type React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { MarketplaceSkillCardRead } from "@/api/generated/model";
import { MarketplaceSkillsTable } from "./MarketplaceSkillsTable";

vi.mock("next/link", () => {
  type LinkProps = React.PropsWithChildren<{
    href: string | { pathname?: string };
  }> &
    Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, "href">;

  return {
    default: ({ href, children, ...props }: LinkProps) => (
      <a href={typeof href === "string" ? href : "#"} {...props}>
        {children}
      </a>
    ),
  };
});

// table-helpers uses useState which works fine in jsdom, but the "use client"
// directive causes no issue in vitest — mock it to keep sorting state simple.
vi.mock("@/components/skills/table-helpers", () => ({
  SKILLS_TABLE_EMPTY_ICON: <span data-testid="empty-icon" />,
  useTableSortingState: () => ({
    resolvedSorting: [{ id: "name", desc: false }],
    handleSortingChange: vi.fn(),
  }),
}));

vi.mock("@/lib/skills-source", () => ({
  packLabelFromUrl: (url: string) => url ?? "Unknown pack",
  packUrlFromSkillSourceUrl: (url: string) => url ?? "",
  packsHrefFromPackUrl: (url: string) => `/skills/packs?url=${url}`,
}));

vi.mock("@/lib/formatters", () => ({
  truncateText: (text: string) => text,
}));

vi.mock("@/components/tables/cell-formatters", () => ({
  dateCell: (value: string) => <span>{value}</span>,
}));

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

describe("MarketplaceSkillsTable", () => {
  it("renders skill name, category, and risk columns", () => {
    render(<MarketplaceSkillsTable skills={[buildSkill()]} />);

    expect(screen.getByText("Web Search")).toBeInTheDocument();
    expect(screen.getByText("research")).toBeInTheDocument();
    // Risk badge renders the risk label
    expect(screen.getByText("low")).toBeInTheDocument();
  });

  it("renders skill description as subtitle text", () => {
    render(
      <MarketplaceSkillsTable
        skills={[buildSkill({ description: "Searches the web." })]}
      />,
    );
    expect(screen.getByText("Searches the web.")).toBeInTheDocument();
  });

  it("renders 'No description provided.' when description is null", () => {
    render(
      <MarketplaceSkillsTable
        skills={[buildSkill({ description: null })]}
      />,
    );
    expect(screen.getByText("No description provided.")).toBeInTheDocument();
  });

  it("renders skill as clickable button when onSkillClick is provided", () => {
    const onSkillClick = vi.fn();
    const skill = buildSkill();

    render(
      <MarketplaceSkillsTable skills={[skill]} onSkillClick={onSkillClick} />,
    );

    const skillButton = screen.getByRole("button", { name: "Web Search" });
    fireEvent.click(skillButton);
    expect(onSkillClick).toHaveBeenCalledWith(skill);
  });

  it("renders skill as plain text when onSkillClick is not provided", () => {
    render(<MarketplaceSkillsTable skills={[buildSkill()]} />);

    expect(
      screen.queryByRole("button", { name: "Web Search" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Web Search")).toBeInTheDocument();
  });

  it("renders Edit link when getEditHref is provided", () => {
    const getEditHref = (skill: MarketplaceSkillCardRead) =>
      `/skills/marketplace/${skill.id}/edit`;

    render(
      <MarketplaceSkillsTable
        skills={[buildSkill()]}
        getEditHref={getEditHref}
      />,
    );

    expect(screen.getByRole("link", { name: "Edit" })).toHaveAttribute(
      "href",
      "/skills/marketplace/skill-1/edit",
    );
  });

  it("calls onDelete when Delete button is clicked", () => {
    const onDelete = vi.fn();
    const skill = buildSkill();

    render(<MarketplaceSkillsTable skills={[skill]} onDelete={onDelete} />);

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(onDelete).toHaveBeenCalledWith(skill);
  });

  it("disables Delete button when isMutating is true", () => {
    render(
      <MarketplaceSkillsTable
        skills={[buildSkill()]}
        onDelete={vi.fn()}
        isMutating={true}
      />,
    );

    expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
  });

  it("renders installed gateway names when provided", () => {
    const skill = buildSkill({ id: "skill-2", name: "Code Runner" });

    render(
      <MarketplaceSkillsTable
        skills={[skill]}
        installedGatewayNamesBySkillId={{
          "skill-2": [{ id: "gw-1", name: "Primary Gateway" }],
        }}
      />,
    );

    expect(screen.getByText("Primary Gateway")).toBeInTheDocument();
  });

  it("renders dash when skill has no installed gateways", () => {
    render(
      <MarketplaceSkillsTable
        skills={[buildSkill({ id: "skill-3" })]}
        installedGatewayNamesBySkillId={{ "skill-3": [] }}
      />,
    );

    expect(screen.getByText("-")).toBeInTheDocument();
  });

  it("renders multiple skills", () => {
    const skills = [
      buildSkill({ id: "skill-a", name: "Alpha" }),
      buildSkill({ id: "skill-b", name: "Beta" }),
    ];

    render(<MarketplaceSkillsTable skills={skills} />);

    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
  });

  it("renders loading state when isLoading is true", () => {
    render(<MarketplaceSkillsTable skills={[]} isLoading={true} />);
    // DataTable renders a loading row/message — the table body should show loading
    expect(screen.getByRole("table")).toBeInTheDocument();
  });

  it("renders empty state when no skills and emptyState provided", () => {
    render(
      <MarketplaceSkillsTable
        skills={[]}
        emptyState={{
          title: "No marketplace skills yet",
          description: "Add packs first.",
        }}
      />,
    );

    expect(screen.getByText("No marketplace skills yet")).toBeInTheDocument();
    expect(screen.getByText("Add packs first.")).toBeInTheDocument();
  });

  it("renders risk badge with unknown label when risk is null", () => {
    render(<MarketplaceSkillsTable skills={[buildSkill({ risk: null })]} />);
    expect(screen.getByText("unknown")).toBeInTheDocument();
  });

  it("renders 'No source' when source and source_url are empty", () => {
    render(
      <MarketplaceSkillsTable
        skills={[buildSkill({ source: null, source_url: "" })]}
      />,
    );
    expect(screen.getByText("No source")).toBeInTheDocument();
  });
});
