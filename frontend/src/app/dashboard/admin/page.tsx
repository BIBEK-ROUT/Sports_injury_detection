"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { authApi, getToken } from "@/lib/api";

const RISK_BADGE: Record<string, { bg: string; color: string }> = {
  low:      { bg: "#dcfce7", color: "#166534" },
  moderate: { bg: "#fef9c3", color: "#854d0e" },
  high:     { bg: "#ffedd5", color: "#c2410c" },
  critical: { bg: "#fee2e2", color: "#b91c1c" },
  pending:  { bg: "#f1f5f9", color: "#64748b" },
};

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

// ─── Types ───────────────────────────────────────────────────────────────────
interface AIUsage {
  model_name: string;
  total_requests: number;
  total_tokens: number;
  today_requests: number;
  today_tokens: number;
  daily_limit: number;
  percent_used: number;
  status: "normal" | "warning";
  last_used_at: string | null;
}

interface Stats {
  total_users: number;
  users_by_role: Record<string, number>;
  active_users: number;
  inactive_users: number;
  total_videos_analyzed: number;
  risk_distribution: Record<string, number>;
  ai_usage?: AIUsage;
}

interface ConfigItem {
  key: string;
  value: string;
  description: string;
  updated_at: string | null;
}

interface ActivityItem {
  session_id: string;
  event: string;
  user_name: string;
  user_email: string;
  user_role: string;
  details?: string;
  filename?: string;
  duration_seconds: number | null;
  risk_level: string;
  created_at: string;
}

// ─── Event Badge Styles ──────────────────────────────────────────────────────
const EVENT_CONFIG: Record<string, { label: string; bg: string; color: string; border: string }> = {
  video_uploaded:       { label: "⬆ Uploaded",     bg: "#dcfce7", color: "#166534", border: "#bbf7d0" },
  uploaded:             { label: "⬆ Uploaded",     bg: "#dcfce7", color: "#166534", border: "#bbf7d0" },
  video_deleted:        { label: "🗑 Deleted",      bg: "#fee2e2", color: "#b91c1c", border: "#fecaca" },
  deleted:              { label: "🗑 Deleted",      bg: "#fee2e2", color: "#b91c1c", border: "#fecaca" },
  report_exported:      { label: "📄 PDF Export",  bg: "#eff6ff", color: "#1d4ed8", border: "#bfdbfe" },
  user_registered:      { label: "👤 New User",    bg: "#f3e8ff", color: "#6b21a8", border: "#e9d5ff" },
  user_linked:          { label: "🔗 Linked",      bg: "#ecfdf5", color: "#047857", border: "#a7f3d0" },
  user_unlinked:        { label: "✂ Unlinked",    bg: "#fff7ed", color: "#c2410c", border: "#fed7aa" },
  user_status_changed:  { label: "⚡ Status",      bg: "#fef3c7", color: "#92400e", border: "#fde68a" },
  user_deleted:         { label: "❌ User Purged", bg: "#fef2f2", color: "#991b1b", border: "#fca5a5" },
};

// ─── Colour Palettes ─────────────────────────────────────────────────────────
const ROLE_COLORS: Record<string, string> = {
  athlete:         "#6366f1",
  coach:           "#0ea5e9",
  physiotherapist: "#10b981",
  scientist:       "#f59e0b",
  admin:           "#ef4444",
};

const RISK_COLORS: Record<string, string> = {
  low:      "#22c55e",
  moderate: "#f59e0b",
  high:     "#f97316",
  critical: "#ef4444",
};

const CONFIG_LABELS: Record<string, string> = {
  maintenance_mode:       "Maintenance Mode",
  ai_chatbot_enabled:     "AI Chatbot",
  allow_new_registrations: "New Registrations",
};

// ─── Stat Card ───────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, color }: { label: string; value: number | string; sub?: string; color: string }) {
  return (
    <div style={{
      background: "#fff", borderRadius: "12px", padding: "22px 24px",
      boxShadow: "0 1px 4px rgba(0,0,0,0.06)", border: "1px solid #e2e8f0",
      flex: 1, minWidth: "180px",
    }}>
      <p style={{ fontSize: "12px", fontWeight: 600, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>{label}</p>
      <p style={{ fontSize: "32px", fontWeight: 800, color, lineHeight: 1 }}>{value}</p>
      {sub && <p style={{ fontSize: "12px", color: "#64748b", marginTop: "6px" }}>{sub}</p>}
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────
export default function AdminPage() {
  const router = useRouter();
  const [stats, setStats]         = useState<Stats | null>(null);
  const [configs, setConfigs]     = useState<ConfigItem[]>([]);
  const [activity, setActivity]   = useState<ActivityItem[]>([]);
  const [loading, setLoading]     = useState(true);
  const [toggling, setToggling]   = useState<string | null>(null);
  const [error, setError]         = useState("");

  const token = getToken();

  useEffect(() => {
    if (!token) { router.push("/login"); return; }

    // Verify admin role — stay on the page even if something fails
    authApi.getMe().then(user => {
      const roleName = user.role?.name ?? (user as any).role;
      if (roleName !== "admin") {
        router.push("/dashboard");
        return;
      }
      loadAll();
    }).catch(err => {
      setError("Session expired. Please log in again.");
      setLoading(false);
    });
  }, []);

  async function loadAll() {
    setLoading(true);
    try {
      // Stats and config are critical — if these fail, show the error banner
      const [statsRes, configRes] = await Promise.all([
        fetch(`${API}/api/admin/stats`,  { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API}/api/admin/config`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (!statsRes.ok || !configRes.ok) throw new Error("Failed to load admin data");
      setStats(await statsRes.json());
      setConfigs(await configRes.json());
    } catch {
      setError("Failed to load admin data. Please refresh.");
    } finally {
      setLoading(false);
    }

    // Activity monitor is optional — failures are silently ignored
    try {
      const activityRes = await fetch(`${API}/api/admin/activity`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (activityRes.ok) setActivity(await activityRes.json());
    } catch {
      // Non-critical — don't show error to admin
    }
  }


  async function handleToggle(key: string, currentValue: string) {
    const newValue = currentValue === "true" ? "false" : "true";
    setToggling(key);
    try {
      const res = await fetch(`${API}/api/admin/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ key, value: newValue }),
      });
      if (!res.ok) throw new Error();
      setConfigs(prev => prev.map(c => c.key === key ? { ...c, value: newValue } : c));
    } catch {
      setError("Failed to update config setting. Please try again.");
    } finally {
      setToggling(null);
    }
  }

  // ── Build chart data ──────────────────────────────────────────────────────
  const roleChartData = stats && stats.users_by_role
    ? Object.entries(stats.users_by_role)
        .filter(([_, value]) => value > 0)
        .map(([name, value]) => ({
          name: name.charAt(0).toUpperCase() + name.slice(1),
          rawKey: name.toLowerCase(),
          value
        }))
    : [];

  const riskChartData = stats && stats.risk_distribution
    ? Object.entries(stats.risk_distribution)
        .filter(([_, value]) => value > 0)
        .map(([name, value]) => {
          const rawKey = name.toLowerCase();
          const displayName = rawKey.charAt(0).toUpperCase() + rawKey.slice(1);
          return { name: displayName, rawKey, value };
        })
    : [];

  // ── Loading ───────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ width: 40, height: 40, border: "3px solid #e2e8f0", borderTopColor: "#6366f1", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 12px" }} />
          <p style={{ color: "#64748b", fontSize: "14px" }}>Loading admin panel...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "1100px" }}>

      {/* Header */}
      <div style={{ marginBottom: "28px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
          <div style={{ width: 36, height: 36, borderRadius: "9px", background: "linear-gradient(135deg,#6366f1,#4f46e5)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <h1 style={{ fontSize: "22px", fontWeight: 800, color: "#0f172a" }}>Admin Dashboard</h1>
        </div>
        <p style={{ color: "#64748b", fontSize: "14px" }}>Platform overview, system health, and configuration management.</p>
      </div>

      {error && (
        <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: "8px", padding: "12px 16px", color: "#b91c1c", fontSize: "14px", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {/* ── Stat Cards ── */}
      <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", marginBottom: "28px" }}>
        <StatCard label="Total Users"     value={stats?.total_users ?? 0}            color="#6366f1" sub={`${stats?.active_users ?? 0} active · ${stats?.inactive_users ?? 0} inactive`} />
        <StatCard label="Videos Analyzed" value={stats?.total_videos_analyzed ?? 0}  color="#0ea5e9" sub="Total AI analyses run" />
        <StatCard label="Active Accounts" value={stats?.active_users ?? 0}           color="#10b981" sub="Currently enabled users" />
        <StatCard label="Deactivated"     value={stats?.inactive_users ?? 0}         color="#ef4444" sub="Suspended accounts" />
      </div>

      {/* ── Charts Row ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "28px" }}>

        {/* Users by Role Donut Chart */}
        <div style={{ background: "#fff", borderRadius: "12px", padding: "24px", boxShadow: "0 1px 4px rgba(0,0,0,0.06)", border: "1px solid #e2e8f0" }}>
          <h2 style={{ fontSize: "15px", fontWeight: 700, color: "#0f172a", marginBottom: "4px" }}>Users by Role</h2>
          <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "16px" }}>Distribution of user roles across the platform</p>
          {roleChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart margin={{ top: 20, bottom: 5, left: 10, right: 10 }}>
                <Pie
                  data={roleChartData}
                  cx="50%" cy="50%"
                  innerRadius={44} outerRadius={66}
                  paddingAngle={3} dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                  labelLine={true}
                >
                  {roleChartData.map(entry => (
                    <Cell key={entry.name} fill={ROLE_COLORS[entry.rawKey] ?? ROLE_COLORS[entry.name.toLowerCase()] ?? "#94a3b8"} />
                  ))}
                </Pie>
                <Tooltip formatter={(val) => [`${val} users`, ""]} />
                <Legend iconType="circle" iconSize={10} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8", fontSize: "14px" }}>No user data yet</div>
          )}
        </div>

        {/* System Risk Distribution Pie Chart */}
        <div style={{ background: "#fff", borderRadius: "12px", padding: "24px", boxShadow: "0 1px 4px rgba(0,0,0,0.06)", border: "1px solid #e2e8f0" }}>
          <h2 style={{ fontSize: "15px", fontWeight: 700, color: "#0f172a", marginBottom: "4px" }}>System Risk Distribution</h2>
          <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "16px" }}>Overall injury risk levels across all analyzed videos</p>
          {riskChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart margin={{ top: 20, bottom: 5, left: 10, right: 10 }}>
                <Pie
                  data={riskChartData}
                  cx="50%" cy="50%"
                  innerRadius={44} outerRadius={66}
                  paddingAngle={3} dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                  labelLine={true}
                >
                  {riskChartData.map(entry => (
                    <Cell key={entry.name} fill={RISK_COLORS[entry.rawKey] ?? RISK_COLORS[entry.name.toLowerCase()] ?? "#94a3b8"} />
                  ))}
                </Pie>
                <Tooltip formatter={(val) => [`${val} sessions`, "Count"]} />
                <Legend iconType="circle" iconSize={10} formatter={(val) => `${val} Risk`} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8", fontSize: "14px" }}>No analysis data yet</div>
          )}
        </div>
      </div>

      {/* ── AI Engine & Token Monitor ── */}
      {stats?.ai_usage && (
        <div style={{ background: "#fff", borderRadius: "12px", padding: "24px", boxShadow: "0 1px 4px rgba(0,0,0,0.06)", border: "1px solid #e2e8f0", marginBottom: "28px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "18px" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "18px" }}>🤖</span>
                <h2 style={{ fontSize: "15px", fontWeight: 700, color: "#0f172a", margin: 0 }}>AI Engine &amp; Token Monitor</h2>
                <span style={{
                  fontSize: "11px", fontWeight: 700, padding: "2px 8px", borderRadius: "20px",
                  background: stats.ai_usage.status === "warning" ? "#fef3c7" : "#dcfce7",
                  color: stats.ai_usage.status === "warning" ? "#92400e" : "#166534",
                }}>
                  {stats.ai_usage.status === "warning" ? "⚠️ High Usage" : "🟢 Operational"}
                </span>
              </div>
              <p style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>
                Live token consumption and safety throttle for LLM recommendations &amp; chatbot.
              </p>
            </div>
            <div style={{ textAlign: "right" }}>
              <span style={{ fontSize: "11px", color: "#64748b" }}>Model: </span>
              <code style={{ fontSize: "11px", background: "#f1f5f9", padding: "2px 6px", borderRadius: "4px", color: "#475569", fontWeight: 600 }}>
                {stats.ai_usage.model_name}
              </code>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "20px" }}>
            <div style={{ padding: "14px 16px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <p style={{ fontSize: "11px", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 4px" }}>Total Tokens Consumed</p>
              <p style={{ fontSize: "22px", fontWeight: 800, color: "#6366f1", margin: 0 }}>{stats.ai_usage.total_tokens.toLocaleString()}</p>
              <p style={{ fontSize: "11px", color: "#64748b", margin: "4px 0 0" }}>Across all sessions &amp; chats</p>
            </div>

            <div style={{ padding: "14px 16px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <p style={{ fontSize: "11px", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 4px" }}>Tokens Used Today</p>
              <p style={{ fontSize: "22px", fontWeight: 800, color: "#0ea5e9", margin: 0 }}>{stats.ai_usage.today_tokens.toLocaleString()}</p>
              <p style={{ fontSize: "11px", color: "#64748b", margin: "4px 0 0" }}>Daily Limit: {stats.ai_usage.daily_limit.toLocaleString()}</p>
            </div>

            <div style={{ padding: "14px 16px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <p style={{ fontSize: "11px", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 4px" }}>AI Requests (Today)</p>
              <p style={{ fontSize: "22px", fontWeight: 800, color: "#10b981", margin: 0 }}>{stats.ai_usage.today_requests}</p>
              <p style={{ fontSize: "11px", color: "#64748b", margin: "4px 0 0" }}>Total Lifetime: {stats.ai_usage.total_requests}</p>
            </div>

            <div style={{ padding: "14px 16px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <p style={{ fontSize: "11px", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 4px" }}>Daily Quota Consumed</p>
              <p style={{ fontSize: "22px", fontWeight: 800, color: stats.ai_usage.percent_used > 80 ? "#ef4444" : "#0f172a", margin: 0 }}>{stats.ai_usage.percent_used}%</p>
              <div style={{ width: "100%", height: "6px", background: "#e2e8f0", borderRadius: "3px", overflow: "hidden", marginTop: "8px" }}>
                <div style={{ width: `${stats.ai_usage.percent_used}%`, height: "100%", background: stats.ai_usage.percent_used > 80 ? "#ef4444" : "#6366f1", transition: "width 0.3s" }} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── System Configuration ── */}
      <div style={{ background: "#fff", borderRadius: "12px", padding: "24px", boxShadow: "0 1px 4px rgba(0,0,0,0.06)", border: "1px solid #e2e8f0" }}>
        <div style={{ marginBottom: "20px" }}>
          <h2 style={{ fontSize: "15px", fontWeight: 700, color: "#0f172a", marginBottom: "4px" }}>System Configuration</h2>
          <p style={{ fontSize: "12px", color: "#94a3b8" }}>Toggle platform features globally. Changes apply instantly for all users.</p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "1px", border: "1px solid #e2e8f0", borderRadius: "10px", overflow: "hidden" }}>
          {configs.map((cfg, i) => {
            const isOn = cfg.value === "true";
            const isLoading = toggling === cfg.key;
            return (
              <div key={cfg.key} style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "16px 20px",
                background: i % 2 === 0 ? "#fff" : "#fafafa",
                borderBottom: i < configs.length - 1 ? "1px solid #f1f5f9" : "none",
              }}>
                <div>
                  <p style={{ fontSize: "14px", fontWeight: 600, color: "#0f172a", marginBottom: "2px" }}>
                    {CONFIG_LABELS[cfg.key] ?? cfg.key}
                  </p>
                  <p style={{ fontSize: "12px", color: "#94a3b8" }}>{cfg.description}</p>
                </div>
                <button
                  id={`toggle-${cfg.key}`}
                  onClick={() => handleToggle(cfg.key, cfg.value)}
                  disabled={isLoading}
                  title={isOn ? "Click to disable" : "Click to enable"}
                  style={{
                    width: "48px", height: "26px", borderRadius: "13px", border: "none", cursor: isLoading ? "wait" : "pointer",
                    background: isOn ? "#6366f1" : "#d1d5db",
                    position: "relative", transition: "background 0.2s", flexShrink: 0,
                  }}
                >
                  <span style={{
                    position: "absolute", top: "3px",
                    left: isOn ? "25px" : "3px",
                    width: "20px", height: "20px", borderRadius: "50%",
                    background: "#fff", transition: "left 0.2s",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
                  }} />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Activity Monitor ── */}
      <div style={{ background: "#fff", borderRadius: "12px", padding: "24px", boxShadow: "0 1px 4px rgba(0,0,0,0.06)", border: "1px solid #e2e8f0", marginTop: "20px" }}>
        <div style={{ marginBottom: "20px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2 style={{ fontSize: "15px", fontWeight: 700, color: "#0f172a", marginBottom: "4px" }}>Activity Monitor</h2>
            <p style={{ fontSize: "12px", color: "#94a3b8" }}>All video analyses across the platform, newest first. Use this to detect suspicious uploads or API abuse.</p>
          </div>
          <button
            onClick={loadAll}
            disabled={loading}
            style={{
              padding: "8px 12px", borderRadius: "6px", border: "1px solid #e2e8f0", background: "#f8fafc",
              color: "#475569", fontSize: "13px", fontWeight: 600, cursor: loading ? "wait" : "pointer",
              display: "flex", alignItems: "center", gap: "6px", transition: "all 0.2s"
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ animation: loading ? "spin 1s linear infinite" : "none" }}>
              <path d="M21 2v6h-6"/><path d="M3 12a9 9 0 1 0 2.1-5.8L2 9"/>
            </svg>
            Refresh
          </button>
        </div>

        {activity.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#94a3b8", fontSize: "14px" }}>No video analyses recorded yet.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
              <thead>
                <tr style={{ background: "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>
                  {["Event", "User", "Email", "Role", "Activity Details", "Risk", "Date"].map(h => (
                    <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontSize: "11px", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {activity.map((a, i) => {
                  const badge = RISK_BADGE[a.risk_level] ?? RISK_BADGE.pending;
                  const evConf = EVENT_CONFIG[a.event] ?? { label: a.event, bg: "#f1f5f9", color: "#475569", border: "#e2e8f0" };
                  const isSevere = a.event.includes("deleted") || a.risk_level === "high" || a.risk_level === "critical";
                  const roleColor = ROLE_COLORS[a.user_role] ?? "#64748b";

                  return (
                    <tr key={`${a.session_id}-${a.event}-${i}`} style={{
                      borderBottom: i < activity.length - 1 ? "1px solid #f1f5f9" : "none",
                      background: isSevere ? "#fffbfb" : i % 2 === 0 ? "#fff" : "#fafafa",
                    }}>
                      {/* Event badge */}
                      <td style={{ padding: "11px 14px", whiteSpace: "nowrap" }}>
                        <span style={{
                          padding: "3px 9px", borderRadius: "20px", fontSize: "11px", fontWeight: 700,
                          background: evConf.bg, color: evConf.color, border: `1px solid ${evConf.border}`,
                        }}>
                          {evConf.label}
                        </span>
                      </td>
                      <td style={{ padding: "11px 14px", fontWeight: 600, color: "#0f172a", whiteSpace: "nowrap" }}>{a.user_name}</td>
                      <td style={{ padding: "11px 14px", color: "#475569" }}>{a.user_email}</td>
                      <td style={{ padding: "11px 14px", whiteSpace: "nowrap" }}>
                        <span style={{ padding: "2px 8px", borderRadius: "20px", fontSize: "11px", fontWeight: 700, background: `${roleColor}18`, color: roleColor, textTransform: "capitalize" }}>
                          {a.user_role}
                        </span>
                      </td>
                      <td style={{ padding: "11px 14px", color: "#334155", maxWidth: "260px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={a.details || a.filename}>
                        {a.details || a.filename || "—"}
                      </td>
                      <td style={{ padding: "11px 14px", whiteSpace: "nowrap" }}>
                        {a.risk_level && a.risk_level !== "—" && a.risk_level !== "pending" ? (
                          <span style={{ padding: "2px 8px", borderRadius: "20px", fontSize: "11px", fontWeight: 700, background: badge.bg, color: badge.color, textTransform: "capitalize" }}>
                            {a.risk_level}
                          </span>
                        ) : (
                          <span style={{ color: "#94a3b8", fontSize: "12px" }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: "11px 14px", color: "#94a3b8", whiteSpace: "nowrap" }}>
                        {new Date(a.created_at).toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
