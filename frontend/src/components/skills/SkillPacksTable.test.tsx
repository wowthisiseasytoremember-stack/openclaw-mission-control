import type React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { SkillPackRead } from "@/api/generated/model";
import { SkillPacksTable } from "./SkillPacksTable";

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

vi.mock("@/components/skills/table-helpers", () => ({
  SKILLS_TABLE_EMPTY_ICON: <span data-testid="empty-icon" />,
  useTableSortingState: () => ({
    resolvedSorting: [{ id: "name", desc: false }],
    handleSortingChange: vi.fn(),
  }),
}));

vi.mock("@/lib/formatters", () => ({
  truncateText: (text: string) => text,
}));

vi.mock("@/components/tables/cell-formatters", () => ({
  dateCell: (value: string) => <span>{value}</span>,
}));

const buildPack = (overrides: Partial<SkillPackRead> = {}): SkillPackRead => ({
  id: "pack-1",
  name: "Core Pack",
  description: "Essential skills for everyday use.",
  source_url: "https://github.com/example/core-skills",
  branch: "main",
  skill_count: 12,
  organization_id: "org-1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  ...overrides,
});

describe("SkillPacksTable", () => {
  it("renders pack name and description", () => {
    render(<SkillPacksTable packs={[buildPack()]} />);

    expect(screen.getByText("Core Pack")).toBeInTheDocument();
    expect(
      screen.getByText("Essential skills for everyday use."),
    ).toBeInTheDocument();
  });

  it("renders 'No description provided.' when description is null", () => {
    render(<SkillPacksTable packs={[buildPack({ description: null })]} />);
    expect(screen.getByText("No description provided.")).toBeInTheDocument();
  });

  it("renders branch name", () => {
    render(<SkillPacksTable packs={[buildPack({ branch: "release" })]} />);
    expect(screen.getByText("release")).toBeInTheDocument();
  });

  it("renders skill count as a link to the marketplace filtered by pack", () => {
    render(<SkillPacksTable packs={[buildPack({ id: "pack-1", skill_count: 12 })]} />);

    const skillCountLink = screen.getByRole("link", { name: "12" });
    expect(skillCountLink).toHaveAttribute(
      "href",
      "/skills/marketplace?packId=pack-1",
    );
  });

  it("renders 0 when skill_count is undefined", () => {
    render(
      <SkillPacksTable packs={[buildPack({ skill_count: undefined })]} />,
    );
    expect(screen.getByRole("link", { name: "0" })).toBeInTheDocument();
  });

  it("renders Sync button when onSync is provided", () => {
    render(<SkillPacksTable packs={[buildPack()]} onSync={vi.fn()} canSync />);
    expect(screen.getByRole("button", { name: "Sync" })).toBeInTheDocument();
  });

  it("does not render Sync button when onSync is not provided", () => {
    render(<SkillPacksTable packs={[buildPack()]} />);
    expect(
      screen.queryByRole("button", { name: "Sync" }),
    ).not.toBeInTheDocument();
  });

  it("calls onSync with the pack when Sync button is clicked", () => {
    const onSync = vi.fn();
    const pack = buildPack();

    render(<SkillPacksTable packs={[pack]} onSync={onSync} canSync />);

    fireEvent.click(screen.getByRole("button", { name: "Sync" }));
    expect(onSync).toHaveBeenCalledWith(pack);
  });

  it("shows Syncing... and disables button for the pack currently syncing", () => {
    const pack = buildPack({ id: "pack-1" });

    render(
      <SkillPacksTable
        packs={[pack]}
        onSync={vi.fn()}
        canSync
        syncingPackIds={new Set(["pack-1"])}
      />,
    );

    const syncButton = screen.getByRole("button", { name: "Syncing..." });
    expect(syncButton).toBeDisabled();
  });

  it("disables Sync button when canSync is false", () => {
    render(
      <SkillPacksTable
        packs={[buildPack()]}
        onSync={vi.fn()}
        canSync={false}
      />,
    );

    expect(screen.getByRole("button", { name: "Sync" })).toBeDisabled();
  });

  it("renders multiple packs", () => {
    const packs = [
      buildPack({ id: "pack-a", name: "Alpha Pack" }),
      buildPack({ id: "pack-b", name: "Beta Pack" }),
    ];

    render(<SkillPacksTable packs={packs} />);

    expect(screen.getByText("Alpha Pack")).toBeInTheDocument();
    expect(screen.getByText("Beta Pack")).toBeInTheDocument();
  });

  it("renders empty state when no packs and emptyState provided", () => {
    render(
      <SkillPacksTable
        packs={[]}
        emptyState={{
          title: "No skill packs yet",
          description: "Add your first pack to get started.",
          actionHref: "/skills/packs/new",
          actionLabel: "Add pack",
        }}
      />,
    );

    expect(screen.getByText("No skill packs yet")).toBeInTheDocument();
    expect(
      screen.getByText("Add your first pack to get started."),
    ).toBeInTheDocument();
  });

  it("renders source URL as a link", () => {
    render(
      <SkillPacksTable
        packs={[buildPack({ source_url: "https://github.com/example/packs" })]}
      />,
    );

    expect(
      screen.getByRole("link", { name: "https://github.com/example/packs" }),
    ).toHaveAttribute("href", "https://github.com/example/packs");
  });
});
