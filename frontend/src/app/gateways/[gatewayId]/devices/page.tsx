"use client";

export const dynamic = "force-dynamic";

import { useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import {
  type ColumnDef,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/auth/clerk";
import { ApiError, customFetch } from "@/api/mutator";
import { DataTable } from "@/components/tables/DataTable";
import { dateCell, pillCell } from "@/components/tables/cell-formatters";
import { DashboardPageLayout } from "@/components/templates/DashboardPageLayout";
import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";
import { truncateText as truncate } from "@/lib/formatters";
import { useOrganizationMembership } from "@/lib/use-organization-membership";

// ---------------------------------------------------------------------------
// Types (manual — not code-generated for this new endpoint)
// ---------------------------------------------------------------------------

type DeviceStatus = "pending" | "approved" | "revoked";

interface GatewayDeviceRead {
  id: string;
  gateway_id: string;
  device_id: string;
  public_key_pem: string;
  name?: string | null;
  status: DeviceStatus;
  first_seen_at: string;
  last_seen_at: string;
  approved_at?: string | null;
  approved_by?: string | null;
  revoked_at?: string | null;
}

interface PaginatedDevices {
  items: GatewayDeviceRead[];
  total: number;
  limit: number;
  offset: number;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const fetchDevices = async (gatewayId: string): Promise<PaginatedDevices> => {
  const resp = await customFetch<{ data: PaginatedDevices; status: number }>(
    `/api/v1/gateways/${gatewayId}/devices`,
    { method: "GET" },
  );
  if (resp.status !== 200) {
    throw new ApiError(resp.status, "Failed to load devices", null);
  }
  return resp.data;
};

const patchDevice = async (
  gatewayId: string,
  deviceId: string,
  updates: { status?: DeviceStatus; name?: string },
): Promise<GatewayDeviceRead> => {
  const resp = await customFetch<{ data: GatewayDeviceRead; status: number }>(
    `/api/v1/gateways/${gatewayId}/devices/${deviceId}`,
    {
      method: "PATCH",
      body: JSON.stringify(updates),
    },
  );
  if (resp.status !== 200) {
    throw new ApiError(resp.status, "Failed to update device", null);
  }
  return resp.data;
};

const deleteDevice = async (
  gatewayId: string,
  deviceId: string,
): Promise<void> => {
  const resp = await customFetch<{ data: unknown; status: number }>(
    `/api/v1/gateways/${gatewayId}/devices/${deviceId}`,
    { method: "DELETE" },
  );
  if (resp.status !== 200) {
    throw new ApiError(resp.status, "Failed to delete device", null);
  }
};

// ---------------------------------------------------------------------------
// Status badge helper
// ---------------------------------------------------------------------------

const STATUS_CLASSES: Record<DeviceStatus, string> = {
  pending:
    "inline-flex items-center rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-semibold text-yellow-800",
  approved:
    "inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800",
  revoked:
    "inline-flex items-center rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-semibold text-rose-800",
};

function StatusBadge({ status }: { status: string }) {
  const cls =
    STATUS_CLASSES[status as DeviceStatus] ??
    "inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600";
  return <span className={cls}>{status}</span>;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

type ActionTarget = {
  device: GatewayDeviceRead;
  action: "approve" | "revoke" | "delete";
};

export default function GatewayDevicesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const params = useParams();
  const { isSignedIn } = useAuth();

  const gatewayIdParam = params?.gatewayId;
  const gatewayId = Array.isArray(gatewayIdParam)
    ? gatewayIdParam[0]
    : gatewayIdParam;

  const { isAdmin } = useOrganizationMembership(isSignedIn);

  const [actionTarget, setActionTarget] = useState<ActionTarget | null>(null);

  const devicesQueryKey = ["gateway-devices", gatewayId];

  const devicesQuery = useQuery<PaginatedDevices, ApiError>({
    queryKey: devicesQueryKey,
    queryFn: () => fetchDevices(gatewayId ?? ""),
    enabled: Boolean(isSignedIn && isAdmin && gatewayId),
    refetchInterval: 15_000,
  });

  const devices = useMemo(
    () => devicesQuery.data?.items ?? [],
    [devicesQuery.data],
  );

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: devicesQueryKey });
  };

  const approveMutation = useMutation<
    GatewayDeviceRead,
    ApiError,
    { deviceId: string }
  >({
    mutationFn: ({ deviceId }) =>
      patchDevice(gatewayId ?? "", deviceId, { status: "approved" }),
    onSuccess: () => {
      setActionTarget(null);
      invalidate();
    },
  });

  const revokeMutation = useMutation<
    GatewayDeviceRead,
    ApiError,
    { deviceId: string }
  >({
    mutationFn: ({ deviceId }) =>
      patchDevice(gatewayId ?? "", deviceId, { status: "revoked" }),
    onSuccess: () => {
      setActionTarget(null);
      invalidate();
    },
  });

  const deleteMutation = useMutation<void, ApiError, { deviceId: string }>({
    mutationFn: ({ deviceId }) => deleteDevice(gatewayId ?? "", deviceId),
    onSuccess: () => {
      setActionTarget(null);
      invalidate();
    },
  });

  const handleConfirm = () => {
    if (!actionTarget) return;
    const deviceId = actionTarget.device.id;
    if (actionTarget.action === "approve") {
      approveMutation.mutate({ deviceId });
    } else if (actionTarget.action === "revoke") {
      revokeMutation.mutate({ deviceId });
    } else if (actionTarget.action === "delete") {
      deleteMutation.mutate({ deviceId });
    }
  };

  const activeMutation =
    actionTarget?.action === "approve"
      ? approveMutation
      : actionTarget?.action === "revoke"
        ? revokeMutation
        : deleteMutation;

  const columns = useMemo<ColumnDef<GatewayDeviceRead>[]>(
    () => [
      {
        accessorKey: "device_id",
        header: "Device ID",
        cell: ({ row }) => (
          <span className="font-mono text-xs text-slate-700">
            {truncate(row.original.device_id, 20)}
          </span>
        ),
      },
      {
        accessorKey: "name",
        header: "Name",
        cell: ({ row }) => (
          <span className="text-sm text-slate-700">
            {row.original.name ?? "—"}
          </span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
      },
      {
        accessorKey: "last_seen_at",
        header: "Last seen",
        cell: ({ row }) =>
          dateCell(row.original.last_seen_at, { relative: true }),
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => {
          const device = row.original;
          return (
            <div className="flex items-center justify-end gap-2">
              {device.status === "pending" && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setActionTarget({ device, action: "approve" })
                  }
                >
                  Approve
                </Button>
              )}
              {device.status !== "revoked" && (
                <Button
                  variant="outline"
                  size="sm"
                  className="text-rose-600 hover:text-rose-700"
                  onClick={() => setActionTarget({ device, action: "revoke" })}
                >
                  Revoke
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                className="text-slate-400 hover:text-rose-600"
                onClick={() => setActionTarget({ device, action: "delete" })}
              >
                Delete
              </Button>
            </div>
          );
        },
      },
    ],
    [],
  );

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: devices,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const dialogTitle =
    actionTarget?.action === "approve"
      ? "Approve device"
      : actionTarget?.action === "revoke"
        ? "Revoke device"
        : "Delete device";

  const dialogDescription =
    actionTarget?.action === "approve" ? (
      <>
        Allow{" "}
        <strong>{actionTarget.device.name ?? actionTarget.device.device_id}</strong>{" "}
        to connect to this gateway.
      </>
    ) : actionTarget?.action === "revoke" ? (
      <>
        Revoke access for{" "}
        <strong>{actionTarget.device.name ?? actionTarget.device.device_id}</strong>
        . The device will be blocked on its next connection attempt.
      </>
    ) : (
      <>
        Permanently delete device{" "}
        <strong>{actionTarget?.device.name ?? actionTarget?.device.device_id}</strong>
        . This cannot be undone.
      </>
    );

  const confirmLabel =
    actionTarget?.action === "approve"
      ? "Approve"
      : actionTarget?.action === "revoke"
        ? "Revoke"
        : "Delete";

  const confirmingLabel =
    actionTarget?.action === "approve"
      ? "Approving…"
      : actionTarget?.action === "revoke"
        ? "Revoking…"
        : "Deleting…";

  return (
    <>
      <DashboardPageLayout
        signedOut={{
          message: "Sign in to manage gateway devices.",
          forceRedirectUrl: `/gateways/${gatewayId}/devices`,
        }}
        title="Paired devices"
        description="Devices that have connected to this gateway using device identity authentication."
        headerActions={
          <Button variant="outline" onClick={() => router.push(`/gateways/${gatewayId}`)}>
            Back to gateway
          </Button>
        }
        isAdmin={isAdmin}
        adminOnlyMessage="Only organization owners and admins can manage gateway devices."
      >
        {devicesQuery.isLoading ? (
          <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
            Loading devices…
          </div>
        ) : devicesQuery.error ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
            {devicesQuery.error.message}
          </div>
        ) : (
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Devices
              </p>
              <span className="text-xs text-slate-500">
                {devices.length} total
              </span>
            </div>
            <DataTable
              table={table}
              isLoading={devicesQuery.isLoading}
              emptyMessage="No devices registered to this gateway."
              rowClassName="hover:bg-slate-50"
              cellClassName="px-6 py-4"
            />
          </div>
        )}
      </DashboardPageLayout>

      <ConfirmActionDialog
        open={!!actionTarget}
        onOpenChange={(open) => {
          if (!open) setActionTarget(null);
        }}
        ariaLabel={dialogTitle}
        title={dialogTitle}
        description={dialogDescription}
        errorMessage={activeMutation.error?.message}
        onConfirm={handleConfirm}
        isConfirming={activeMutation.isPending}
        confirmLabel={confirmLabel}
        confirmingLabel={confirmingLabel}
      />
    </>
  );
}
