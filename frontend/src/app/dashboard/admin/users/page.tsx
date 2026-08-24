"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authApi, getToken } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

// ─── Types ───────────────────────────────────────────────────────────────────
interface PlatformUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

const ROLE_BADGE_COLORS: Record<string, { bg: string; color: string }> = {
  athlete:         { bg: "#ede9fe", color: "#6d28d9" },
  coach:           { bg: "#e0f2fe", color: "#0369a1" },
  physiotherapist: { bg: "#dcfce7", color: "#166534" },
  scientist:       { bg: "#fef9c3", color: "#854d0e" },
  admin:           { bg: "#fee2e2", color: "#b91c1c" },
};

// ─── Modal: Confirm Action ────────────────────────────────────────────────────
function ConfirmModal({
  user, action, onConfirm, onCancel, loading,
}: {
  user: PlatformUser;
  action: "deactivate" | "activate" | "delete";
  onConfirm: (reason: string) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [reason, setReason] = useState("");
  const isDelete     = action === "delete";
  const isDeactivate = action === "deactivate";
  const title        = isDelete ? "Delete Account" : isDeactivate ? "Deactivate Account" : "Activate Account";
  const accentColor  = isDelete ? "#ef4444" : isDeactivate ? "#f97316" : "#10b981";

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }}>
      <div style={{ background: "#fff", borderRadius: "16px", padding: "28px", width: "420px", boxShadow: "0 20px 60px rgba(0,0,0,0.2)" }}>
        <h3 style={{ fontSize: "17px", fontWeight: 700, color: "#0f172a", marginBottom: "6px" }}>{title}</h3>
        <p style={{ fontSize: "13px", color: "#64748b", marginBottom: "16px" }}>
          {isDelete
            ? `This will permanently delete ${user.first_name} ${user.last_name}'s account and ALL their videos and data. This cannot be undone.`
            : isDeactivate
            ? `${user.first_name} ${user.last_name} will be suspended and unable to log in.`
            : `${user.first_name} ${user.last_name}'s account will be re-activated.`
          }
        </p>

        {(isDelete || isDeactivate) && (
          <div style={{ marginBottom: "16px" }}>
            <label style={{ display: "block", fontSize: "13px", fontWeight: 600, color: "#374151", marginBottom: "6px" }}>
              Reason (will be included in the notification email once the email service is set up)
            </label>
            <select
              value={reason}
              onChange={e => setReason(e.target.value)}
              style={{ width: "100%", padding: "9px 12px", borderRadius: "8px", border: "1px solid #d1d5db", fontSize: "13px", color: "#374151", fontFamily: "inherit", background: "#fff" }}
            >
              <option value="">Select a reason...</option>
              <option value="Inappropriate content uploaded">Inappropriate content uploaded</option>
              <option value="Suspicious/spam activity detected">Suspicious/spam activity detected</option>
              <option value="Impersonation of a professional">Impersonation of a professional</option>
              <option value="Consent violation (athlete data misuse)">Consent violation (athlete data misuse)</option>
              <option value="Account security risk">Account security risk</option>
              <option value="Violation of platform terms of service">Violation of platform terms of service</option>
            </select>
          </div>
        )}

        <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
          <button
            onClick={onCancel}
            disabled={loading}
            style={{ padding: "9px 18px", borderRadius: "8px", border: "1px solid #e2e8f0", background: "#fff", fontSize: "13px", fontWeight: 600, color: "#64748b", cursor: "pointer", fontFamily: "inherit" }}
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(reason)}
            disabled={loading || ((isDelete || isDeactivate) && !reason)}
            style={{
              padding: "9px 18px", borderRadius: "8px", border: "none",
              background: loading ? "#d1d5db" : accentColor,
              fontSize: "13px", fontWeight: 700, color: "#fff", cursor: loading ? "not-allowed" : "pointer",
              fontFamily: "inherit", transition: "background 0.15s",
            }}
          >
            {loading ? "Processing..." : isDelete ? "Delete Permanently" : isDeactivate ? "Deactivate" : "Activate"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function UserManagementPage() {
  const router  = useRouter();
  const token   = getToken();
  const [users, setUsers]           = useState<PlatformUser[]>([]);
  const [filtered, setFiltered]     = useState<PlatformUser[]>([]);
  const [search, setSearch]         = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [loading, setLoading]       = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [modal, setModal]   = useState<{ user: PlatformUser; action: "deactivate" | "activate" | "delete" } | null>(null);
  const [toast, setToast]   = useState<{ msg: string; type: "success" | "error" } | null>(null);

  useEffect(() => {
    if (!token) { router.push("/login"); return; }
    authApi.getMe().then(me => {
      if (me.role?.name !== "admin") { router.push("/dashboard"); return; }
      loadUsers();
    }).catch(() => router.push("/login"));
  }, []);

  useEffect(() => {
    let result = users;
    if (roleFilter !== "all") result = result.filter(u => u.role === roleFilter);
    if (search) result = result.filter(u =>
      `${u.first_name} ${u.last_name} ${u.email}`.toLowerCase().includes(search.toLowerCase())
    );
    setFiltered(result);
  }, [users, search, roleFilter]);

  async function loadUsers() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/admin/users`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error();
      setUsers(await res.json());
    } catch {
      showToast("Failed to load users.", "error");
    } finally {
      setLoading(false);
    }
  }

  function showToast(msg: string, type: "success" | "error") {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  }

  async function handleConfirm(reason: string) {
    if (!modal) return;
    setActionLoading(true);
    try {
      if (modal.action === "delete") {
        const res = await fetch(`${API}/api/admin/users/${modal.user.id}`, {
          method: "DELETE", headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error();
        setUsers(prev => prev.filter(u => u.id !== modal.user.id));
        showToast(`${modal.user.first_name} ${modal.user.last_name}'s account has been permanently deleted.`, "success");
      } else {
        const isActivating = modal.action === "activate";
        const res = await fetch(`${API}/api/admin/users/${modal.user.id}/status`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ is_active: isActivating, reason }),
        });
        if (!res.ok) throw new Error();
        setUsers(prev => prev.map(u => u.id === modal.user.id ? { ...u, is_active: isActivating } : u));
        showToast(`${modal.user.first_name} ${modal.user.last_name}'s account has been ${isActivating ? "activated" : "deactivated"}.`, "success");
      }
    } catch {
      showToast("Action failed. Please try again.", "error");
    } finally {
      setActionLoading(false);
      setModal(null);
    }
  }

  return (
    <div style={{ maxWidth: "1100px" }}>
      {/* Toast */}
      {toast && (
        <div style={{
          position: "fixed", top: "20px", right: "20px", zIndex: 2000,
          background: toast.type === "success" ? "#f0fdf4" : "#fef2f2",
          border: `1px solid ${toast.type === "success" ? "#86efac" : "#fca5a5"}`,
          color: toast.type === "success" ? "#166534" : "#b91c1c",
          borderRadius: "10px", padding: "12px 18px", fontSize: "13px", fontWeight: 600,
          boxShadow: "0 4px 20px rgba(0,0,0,0.1)",
        }}>
          {toast.msg}
        </div>
      )}

      {/* Modal */}
      {modal && (
        <ConfirmModal
          user={modal.user} action={modal.action}
          onConfirm={handleConfirm} onCancel={() => setModal(null)} loading={actionLoading}
        />
      )}

      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "22px", fontWeight: 800, color: "#0f172a", marginBottom: "4px" }}>User Management</h1>
        <p style={{ color: "#64748b", fontSize: "14px" }}>View, search, activate, deactivate, or permanently delete user accounts.</p>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "16px", flexWrap: "wrap" }}>
        <input
          type="text" placeholder="Search by name or email..."
          value={search} onChange={e => setSearch(e.target.value)}
          style={{ flex: 1, minWidth: "200px", padding: "9px 14px", borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: "13px", fontFamily: "inherit", outline: "none" }}
        />
        <select
          value={roleFilter} onChange={e => setRoleFilter(e.target.value)}
          style={{ padding: "9px 14px", borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: "13px", fontFamily: "inherit", background: "#fff" }}
        >
          <option value="all">All Roles</option>
          <option value="athlete">Athletes</option>
          <option value="coach">Coaches</option>
          <option value="physiotherapist">Physiotherapists</option>
          <option value="scientist">Scientists</option>
        </select>
        <span style={{ padding: "9px 14px", background: "#f1f5f9", borderRadius: "8px", fontSize: "13px", color: "#475569", fontWeight: 600 }}>
          {filtered.length} user{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Table */}
      <div style={{ background: "#fff", borderRadius: "12px", border: "1px solid #e2e8f0", overflow: "hidden", boxShadow: "0 1px 4px rgba(0,0,0,0.06)" }}>
        {loading ? (
          <div style={{ padding: "60px", textAlign: "center", color: "#94a3b8" }}>Loading users...</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: "60px", textAlign: "center", color: "#94a3b8" }}>No users found</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>
                {["Name", "Email", "Role", "Joined", "Status", "Actions"].map(h => (
                  <th key={h} style={{ padding: "12px 16px", textAlign: "left", fontSize: "11px", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((u, i) => {
                const badge = ROLE_BADGE_COLORS[u.role] ?? { bg: "#f1f5f9", color: "#475569" };
                return (
                  <tr key={u.id} style={{ borderBottom: i < filtered.length - 1 ? "1px solid #f1f5f9" : "none", background: i % 2 === 0 ? "#fff" : "#fafafa" }}>
                    <td style={{ padding: "14px 16px", fontSize: "14px", fontWeight: 600, color: "#0f172a" }}>
                      {u.first_name} {u.last_name}
                    </td>
                    <td style={{ padding: "14px 16px", fontSize: "13px", color: "#475569" }}>{u.email}</td>
                    <td style={{ padding: "14px 16px" }}>
                      <span style={{ padding: "3px 10px", borderRadius: "20px", fontSize: "11px", fontWeight: 700, background: badge.bg, color: badge.color }}>
                        {u.role}
                      </span>
                    </td>
                    <td style={{ padding: "14px 16px", fontSize: "12px", color: "#94a3b8" }}>
                      {new Date(u.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })}
                    </td>
                    <td style={{ padding: "14px 16px" }}>
                      <span style={{
                        padding: "3px 10px", borderRadius: "20px", fontSize: "11px", fontWeight: 700,
                        background: u.is_active ? "#dcfce7" : "#fee2e2",
                        color: u.is_active ? "#166534" : "#b91c1c",
                      }}>
                        {u.is_active ? "Active" : "Suspended"}
                      </span>
                    </td>
                    <td style={{ padding: "14px 16px" }}>
                      {u.role !== "admin" && (
                        <div style={{ display: "flex", gap: "8px" }}>
                          {u.is_active ? (
                            <button
                              id={`deactivate-${u.id}`}
                              onClick={() => setModal({ user: u, action: "deactivate" })}
                              style={{ padding: "5px 12px", borderRadius: "6px", border: "1px solid #fed7aa", background: "#fff7ed", color: "#c2410c", fontSize: "12px", fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}
                            >
                              Deactivate
                            </button>
                          ) : (
                            <button
                              id={`activate-${u.id}`}
                              onClick={() => setModal({ user: u, action: "activate" })}
                              style={{ padding: "5px 12px", borderRadius: "6px", border: "1px solid #86efac", background: "#f0fdf4", color: "#166534", fontSize: "12px", fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}
                            >
                              Activate
                            </button>
                          )}
                          <button
                            id={`delete-${u.id}`}
                            onClick={() => setModal({ user: u, action: "delete" })}
                            style={{ padding: "5px 12px", borderRadius: "6px", border: "1px solid #fca5a5", background: "#fef2f2", color: "#b91c1c", fontSize: "12px", fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}
                          >
                            Delete
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
