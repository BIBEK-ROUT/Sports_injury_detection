"use client";
import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { authApi, getToken, removeToken, notificationApi, NotificationItem } from "@/lib/api";

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: { id: number; name: string };
}

const VIDEO_ICON = <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>;
const GRID_ICON  = <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>;
const USER_ICON  = <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>;
const TEAM_ICON  = <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>;
const CHART_ICON = <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>;

function getNavItems(role: string) {

  const SHIELD_ICON = <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>;
  const PEOPLE_ICON = <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>;
  const SETTINGS_ICON = <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>;

  switch (role) {
    case "admin":
      return [
        { href: "/dashboard/admin",       label: "Admin Panel",      icon: SHIELD_ICON },
        { href: "/dashboard/admin/users", label: "User Management",  icon: PEOPLE_ICON },
        { href: "/dashboard/profile",     label: "Account",          icon: USER_ICON },
      ];
    case "coach":
      return [
        { href: "/dashboard",          label: "Overview",    icon: GRID_ICON },
        { href: "/dashboard/athletes", label: "My Athletes", icon: TEAM_ICON },
        { href: "/dashboard/profile",  label: "Account",     icon: USER_ICON },
      ];
    case "physiotherapist":
      return [
        { href: "/dashboard",          label: "Overview",  icon: GRID_ICON },
        { href: "/dashboard/athletes", label: "Athletes",  icon: TEAM_ICON },
        { href: "/dashboard/profile",  label: "Account",   icon: USER_ICON },
      ];
    case "scientist":
      return [
        { href: "/dashboard",          label: "Overview",     icon: GRID_ICON },
        { href: "/dashboard/athletes", label: "All Athletes", icon: TEAM_ICON },
        { href: "/dashboard/profile",  label: "Account",      icon: USER_ICON },
      ];
    default: // athlete
      return [
        { href: "/dashboard",          label: "Overview",        icon: GRID_ICON },
        { href: "/dashboard/analyze",  label: "Analyze Video",   icon: VIDEO_ICON },
        { href: "/dashboard/profile",  label: "Athlete Profile", icon: USER_ICON },
      ];
  }
}


export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [maintenance, setMaintenance] = useState(false);

  // Notification state for Coach / Physio
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [showNotifs, setShowNotifs] = useState(false);
  const notifDropdownRef = useRef<HTMLDivElement>(null);

  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

  // Fetch notifications helper
  const loadNotifications = async (currentUser: User) => {
    if (currentUser?.role?.name === "coach" || currentUser?.role?.name === "physiotherapist") {
      try {
        const notifs = await notificationApi.getNotifications();
        setNotifications(notifs);
      } catch {
        // Silent fail if network blip
      }
    }
  };

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }

    // Fetch public config and user in parallel
    Promise.all([
      authApi.getMe(),
      fetch(`${API}/api/public/config`).then(r => r.json()).catch(() => ({})),
    ]).then(([userData, config]) => {
      setUser(userData);
      // Maintenance mode blocks everyone EXCEPT admins
      if (config.maintenance_mode === "true" && userData.role?.name !== "admin") {
        setMaintenance(true);
      }
      loadNotifications(userData);
    }).catch(() => { removeToken(); router.push("/login"); })
      .finally(() => setLoading(false));
  }, [router]);

  // Periodic polling for notifications (every 15s) for Coach & Physio
  useEffect(() => {
    if (!user || (user.role?.name !== "coach" && user.role?.name !== "physiotherapist")) return;

    const interval = setInterval(() => {
      loadNotifications(user);
    }, 15000);

    return () => clearInterval(interval);
  }, [user]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (notifDropdownRef.current && !notifDropdownRef.current.contains(event.target as Node)) {
        setShowNotifs(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleDismissNotif = async (notifId: string, athleteId: string, riskLevel?: string) => {
    // Optimistic UI update: immediately remove from dropdown
    setNotifications(prev => prev.filter(n => n.id !== notifId));
    try {
      await notificationApi.dismissNotification(notifId);
    } catch {
      // background error ignored
    }
    setShowNotifs(false);
    if (riskLevel === "unlinked") {
      router.push("/dashboard/athletes");
    } else {
      router.push(`/dashboard/athletes/${athleteId}`);
    }
  };

  const handleClearAll = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setNotifications([]);
    try {
      await notificationApi.clearAll();
    } catch {
      // background error ignored
    }
  };

  if (loading) {
    return (
      <div style={{
        minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
        background: "#0f172a", color: "#94a3b8", fontSize: "14px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{ width: 18, height: 18, border: "2px solid #38bdf8", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
          Loading SportGuard...
        </div>
      </div>
    );
  }

  // ── Maintenance Mode Screen (blocks all non-admin users) ──────────────────
  if (maintenance) {
    return (
      <div style={{
        minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
        background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        fontFamily: "inherit",
      }}>
        <div style={{ textAlign: "center", maxWidth: "480px", padding: "0 24px" }}>
          <div style={{
            width: 72, height: 72, borderRadius: "18px",
            background: "linear-gradient(135deg,#f59e0b,#d97706)",
            display: "flex", alignItems: "center", justifyContent: "center",
            margin: "0 auto 24px",
          }}>
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>
            </svg>
          </div>
          <h1 style={{ fontSize: "26px", fontWeight: 800, color: "#f8fafc", marginBottom: "12px" }}>
            System Under Maintenance
          </h1>
          <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: 1.6, marginBottom: "24px" }}>
            The platform is temporarily unavailable while we perform scheduled system updates.
            We apologize for the inconvenience and will be back shortly.
          </p>
          <div style={{
            background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "12px", padding: "18px 22px",
          }}>
            <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "6px" }}>Need urgent support or assistance?</p>
            <a
              href="mailto:sportguardsupport@gmail.com"
              style={{ fontSize: "15px", color: "#38bdf8", textDecoration: "none", fontWeight: 700, display: "inline-flex", alignItems: "center", gap: "6px" }}
            >
              ✉️ sportguardsupport@gmail.com
            </a>
          </div>
        </div>
      </div>
    );
  }

  const isProfessional = user?.role?.name === "coach" || user?.role?.name === "physiotherapist";

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#f8fafc" }}>

      {/* ── Sidebar ── */}
      <aside style={{
        width: "228px",
        background: "#ffffff",
        borderRight: "1px solid #e2e8f0",
        display: "flex",
        flexDirection: "column",
        position: "fixed",
        top: 0, left: 0,
        height: "100vh",
        zIndex: 40,
      }}>
        {/* Logo */}
        <div style={{
          padding: "18px 20px",
          borderBottom: "1px solid #f1f5f9",
          display: "flex",
          alignItems: "center",
          gap: "10px",
        }}>
          <div style={{
            width: "30px", height: "30px",
            background: "#2563eb", borderRadius: "7px",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
          </div>
          <span style={{ fontWeight: 700, fontSize: "15px", color: "#0f172a" }}>SportGuard</span>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: "12px 10px" }}>
          {getNavItems(user?.role?.name ?? "athlete").map(item => {
            const active = pathname === item.href;
            return (
              <Link key={item.href} href={item.href} style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "9px 12px",
                borderRadius: "8px",
                textDecoration: "none",
                fontWeight: active ? 600 : 500,
                fontSize: "14px",
                color: active ? "#1d4ed8" : "#475569",
                background: active ? "#eff6ff" : "transparent",
                marginBottom: "2px",
                transition: "all 0.1s",
              }}
                onMouseEnter={e => { if (!active) (e.currentTarget as HTMLElement).style.background = "#f8fafc"; }}
                onMouseLeave={e => { if (!active) (e.currentTarget as HTMLElement).style.background = "transparent"; }}
              >
                {item.icon}
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* User */}
        {user && (
          <div style={{ padding: "12px 16px", borderTop: "1px solid #f1f5f9" }}>
            <div style={{
              padding: "12px",
              background: "#f8fafc",
              borderRadius: "8px",
              marginBottom: "8px",
            }}>
              <p style={{ fontWeight: 600, fontSize: "13px", color: "#0f172a", marginBottom: "2px" }}>
                {user.first_name} {user.last_name}
              </p>
              <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "6px" }}>{user.email}</p>
              <span className="sg-badge sg-badge-blue" style={{ fontSize: "11px" }}>
                {user.role.name}
              </span>
            </div>
            <button
              onClick={() => { removeToken(); router.push("/login"); }}
              style={{
                width: "100%",
                padding: "8px 12px",
                background: "transparent",
                border: "1px solid #e2e8f0",
                borderRadius: "7px",
                fontSize: "13px",
                fontWeight: 500,
                color: "#64748b",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                transition: "all 0.1s",
                fontFamily: "inherit",
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.background = "#fee2e2";
                (e.currentTarget as HTMLElement).style.color = "#b91c1c";
                (e.currentTarget as HTMLElement).style.borderColor = "#fca5a5";
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.background = "transparent";
                (e.currentTarget as HTMLElement).style.color = "#64748b";
                (e.currentTarget as HTMLElement).style.borderColor = "#e2e8f0";
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
              Sign Out
            </button>
          </div>
        )}
      </aside>

      {/* ── Main Container with Top Bar ── */}
      <div style={{ flex: 1, marginLeft: "228px", display: "flex", flexDirection: "column", minHeight: "100vh" }}>
        
        {/* Top Header Bar for Professionals with Notification Bell */}
        {isProfessional && (
          <header style={{
            height: "56px",
            background: "#ffffff",
            borderBottom: "1px solid #e2e8f0",
            padding: "0 32px",
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            position: "sticky",
            top: 0,
            zIndex: 30,
          }}>
            <div style={{ position: "relative" }} ref={notifDropdownRef}>
              <button
                onClick={() => setShowNotifs(prev => !prev)}
                title="Notifications"
                style={{
                  background: showNotifs ? "#eff6ff" : "transparent",
                  border: "1px solid",
                  borderColor: showNotifs ? "#bfdbfe" : "#e2e8f0",
                  borderRadius: "8px",
                  width: "38px",
                  height: "38px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                  position: "relative",
                  color: showNotifs ? "#2563eb" : "#475569",
                  transition: "all 0.15s ease",
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                  <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
                </svg>

                {/* Red Badge with count */}
                {notifications.length > 0 && (
                  <span style={{
                    position: "absolute",
                    top: "-4px",
                    right: "-4px",
                    background: "#ef4444",
                    color: "#ffffff",
                    fontSize: "11px",
                    fontWeight: 700,
                    borderRadius: "9999px",
                    minWidth: "18px",
                    height: "18px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "0 4px",
                    boxShadow: "0 2px 4px rgba(239, 68, 68, 0.4)",
                    animation: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
                  }}>
                    {notifications.length}
                  </span>
                )}
              </button>

              {/* Dropdown Menu */}
              {showNotifs && (
                <div style={{
                  position: "absolute",
                  top: "46px",
                  right: 0,
                  width: "360px",
                  background: "#ffffff",
                  borderRadius: "12px",
                  boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
                  border: "1px solid #e2e8f0",
                  zIndex: 50,
                  overflow: "hidden",
                }}>
                  {/* Header */}
                  <div style={{
                    padding: "14px 16px",
                    borderBottom: "1px solid #f1f5f9",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    background: "#f8fafc",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontWeight: 700, fontSize: "14px", color: "#0f172a" }}>Injury Alerts</span>
                      {notifications.length > 0 && (
                        <span style={{
                          background: "#fee2e2",
                          color: "#991b1b",
                          fontSize: "11px",
                          fontWeight: 700,
                          padding: "2px 6px",
                          borderRadius: "4px",
                        }}>
                          {notifications.length} new
                        </span>
                      )}
                    </div>
                    {notifications.length > 0 && (
                      <button
                        onClick={handleClearAll}
                        style={{
                          background: "transparent",
                          border: "none",
                          color: "#64748b",
                          fontSize: "12px",
                          fontWeight: 600,
                          cursor: "pointer",
                          padding: "4px 6px",
                          borderRadius: "4px",
                        }}
                        onMouseEnter={e => (e.currentTarget.style.color = "#0f172a")}
                        onMouseLeave={e => (e.currentTarget.style.color = "#64748b")}
                      >
                        Clear all
                      </button>
                    )}
                  </div>

                  {/* Notification List */}
                  <div style={{ maxHeight: "340px", overflowY: "auto" }}>
                    {notifications.length === 0 ? (
                      <div style={{ padding: "32px 16px", textAlign: "center" }}>
                        <div style={{
                          width: "40px", height: "40px", borderRadius: "50%",
                          background: "#f0fdf4", color: "#16a34a",
                          display: "flex", alignItems: "center", justifyContent: "center",
                          margin: "0 auto 10px",
                        }}>
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12"/>
                          </svg>
                        </div>
                        <p style={{ fontWeight: 600, fontSize: "14px", color: "#1e293b", marginBottom: "4px" }}>
                          All clear!
                        </p>
                        <p style={{ fontSize: "12px", color: "#94a3b8" }}>
                          No high-risk injury alerts from your athletes.
                        </p>
                      </div>
                    ) : (
                      notifications.map(notif => {
                        const isUnlink = notif.risk_level === "unlinked";
                        const badgeColor = isUnlink ? "#92400e" : notif.risk_level === "critical" ? "#b91c1c" : "#b45309";
                        const badgeBg = isUnlink ? "#fef3c7" : notif.risk_level === "critical" ? "#fee2e2" : "#fef3c7";
                        const dotColor = isUnlink ? "#d97706" : notif.risk_level === "critical" ? "#ef4444" : "#f59e0b";

                        return (
                          <div
                            key={notif.id}
                            onClick={() => handleDismissNotif(notif.id, notif.athlete_id, notif.risk_level)}
                            style={{
                              padding: "12px 16px",
                              borderBottom: "1px solid #f1f5f9",
                              cursor: "pointer",
                              transition: "background 0.15s",
                              display: "flex",
                              gap: "12px",
                              alignItems: "flex-start",
                            }}
                            onMouseEnter={e => (e.currentTarget.style.background = "#f8fafc")}
                            onMouseLeave={e => (e.currentTarget.style.background = "#ffffff")}
                          >
                            <div style={{
                              width: "8px", height: "8px",
                              borderRadius: "50%",
                              background: dotColor,
                              marginTop: "6px",
                              flexShrink: 0,
                            }} />
                            <div style={{ flex: 1 }}>
                              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
                                <span style={{ fontWeight: 700, fontSize: "13px", color: "#0f172a" }}>
                                  {notif.athlete_name}
                                </span>
                                <span style={{
                                  fontSize: "10px",
                                  fontWeight: 700,
                                  textTransform: "uppercase",
                                  color: badgeColor,
                                  background: badgeBg,
                                  padding: "1px 6px",
                                  borderRadius: "4px",
                                }}>
                                  {isUnlink ? "✂️ Unlinked" : notif.risk_level}
                                </span>
                              </div>
                              <p style={{ fontSize: "12px", color: "#475569", lineHeight: 1.4, margin: "0 0 6px 0" }}>
                                {notif.message}
                              </p>
                              <span style={{ fontSize: "11px", color: "#94a3b8" }}>
                                {new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · {isUnlink ? "Click to view roster" : "Click to review"}
                              </span>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              )}
            </div>
          </header>
        )}

        {/* ── Page Content ── */}
        <main style={{ flex: 1, padding: "32px" }}>
          {children}
        </main>
      </div>
    </div>
  );
}
