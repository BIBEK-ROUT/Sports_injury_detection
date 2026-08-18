"use client";
import { useState, FormEvent, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/lib/api";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!token) {
      setError("Reset token is missing. Please request a new link.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const data = await authApi.resetPassword(token, password);
      setSuccess(data.message || "Your password has been successfully reset.");
      setTimeout(() => {
        router.replace("/login");
      }, 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to reset password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ width: "100%", maxWidth: "380px" }}>
      <h1 style={{ fontSize: "24px", fontWeight: 700, color: "#0f172a", marginBottom: "6px" }}>
        Set new password
      </h1>
      <p style={{ color: "#64748b", fontSize: "14px", marginBottom: "28px" }}>
        Choose a secure, strong password for your account
      </p>

      {success ? (
        <div style={{
          background: "#ecfdf5",
          border: "1px solid #10b981",
          color: "#065f46",
          padding: "16px",
          borderRadius: "8px",
          fontSize: "14px",
          lineHeight: 1.5,
          marginBottom: "24px",
        }}>
          {success} Redirecting to login page...
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {error && <div className="sg-alert sg-alert-error">{error}</div>}
          {!token && (
            <div className="sg-alert sg-alert-error">
              Invalid or expired link. Please{" "}
              <Link href="/forgot-password" style={{ color: "inherit", fontWeight: "bold" }}>
                request a new one
              </Link>.
            </div>
          )}

          <div>
            <label className="sg-label" htmlFor="password">New Password</label>
            <input
              id="password"
              type="password"
              className="sg-input"
              placeholder="Min 6 characters"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              disabled={!token}
            />
          </div>

          <div>
            <label className="sg-label" htmlFor="confirmPassword">Confirm New Password</label>
            <input
              id="confirmPassword"
              type="password"
              className="sg-input"
              placeholder="Re-enter password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              required
              disabled={!token}
            />
          </div>

          <button
            type="submit"
            className="sg-btn sg-btn-primary"
            disabled={loading || !token}
            style={{ width: "100%", padding: "12px", fontSize: "15px", marginTop: "4px" }}
          >
            {loading ? <><span className="sg-spinner" /> Resetting...</> : "Reset Password"}
          </button>
        </form>
      )}

      <hr className="sg-divider" style={{ margin: "24px 0" }} />

      <p style={{ textAlign: "center", fontSize: "14px", color: "#64748b" }}>
        Back to{" "}
        <Link href="/login" style={{ color: "#2563eb", fontWeight: 600, textDecoration: "none" }}>
          Sign in
        </Link>
      </p>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <div style={{
      minHeight: "100vh",
      background: "#f8fafc",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "40px 24px",
    }}>
      <Suspense fallback={
        <div style={{ textAlign: "center", color: "#64748b" }}>
          <span className="sg-spinner" style={{ marginRight: "8px" }} /> Loading password reset...
        </div>
      }>
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}
