"use client";
import { useState, FormEvent } from "react";
import Link from "next/link";
import { authApi } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      const data = await authApi.forgotPassword(email);
      setSuccess(data.message || "A password reset link has been sent to your email.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to request password reset.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: "100vh",
      background: "#f8fafc",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "40px 24px",
    }}>
      <div style={{ width: "100%", maxWidth: "380px" }}>
        <Link href="/login" style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          color: "#64748b",
          fontSize: "13px",
          textDecoration: "none",
          marginBottom: "32px",
          fontWeight: 500,
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
          Back to login
        </Link>

        <h1 style={{ fontSize: "24px", fontWeight: 700, color: "#0f172a", marginBottom: "6px" }}>
          Reset your password
        </h1>
        <p style={{ color: "#64748b", fontSize: "14px", marginBottom: "28px", lineHeight: 1.5 }}>
          Enter the email address associated with your account and we&apos;ll send you a link to reset your password.
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
            {success}
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {error && <div className="sg-alert sg-alert-error">{error}</div>}

            <div>
              <label className="sg-label" htmlFor="email">Email address</label>
              <input
                id="email"
                type="email"
                className="sg-input"
                placeholder="you@example.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            <button
              type="submit"
              className="sg-btn sg-btn-primary"
              disabled={loading}
              style={{ width: "100%", padding: "12px", fontSize: "15px", marginTop: "4px" }}
            >
              {loading ? <><span className="sg-spinner" /> Sending...</> : "Send reset link"}
            </button>
          </form>
        )}

        <hr className="sg-divider" style={{ margin: "24px 0" }} />

        <p style={{ textAlign: "center", fontSize: "14px", color: "#64748b" }}>
          Remember your password?{" "}
          <Link href="/login" style={{ color: "#2563eb", fontWeight: 600, textDecoration: "none" }}>
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
