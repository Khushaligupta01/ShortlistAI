"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { saveTokens } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const tokens = await api.login(email, password);
      saveTokens(tokens);

      // Determine where to redirect based on role
      const user = await api.getCurrentUser();
      if (user.role === "client_hiring_manager") {
        router.push("/client");
      } else {
        router.push("/dashboard");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  function handlePrefill(userEmail: string, userPass: string) {
    setEmail(userEmail);
    setPassword(userPass);
  }

  return (
    <div className="min-h-screen bg-[#FAF9F6] flex flex-col items-center justify-center px-4 py-12 selection:bg-[#EDE5D9] selection:text-[#292722]">
      <div className="w-full max-w-md">
        {/* Logo / Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#756653] text-[#FAF9F6] text-xl font-black shadow-xs mb-3">
            S
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#292722]">
            ShortlistAI
          </h1>
          <p className="text-sm text-[#6F6A61] mt-1">
            Evidence-based AI resume screening & client shortlist platform
          </p>
        </div>

        {/* Elevated Login Card */}
        <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] shadow-xs p-8 sm:p-9 transition-all">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-[#292722]">
              Sign in to your account
            </h2>
            <p className="text-xs text-[#918A80] mt-0.5">
              Enter your corporate credentials to access the workspace
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Error Message */}
            {error && (
              <div className="bg-[#FDF0F0] border border-[#EFC2C2] rounded-xl px-4 py-3 text-xs text-[#7A2525] flex items-center gap-2">
                <svg className="w-4 h-4 shrink-0 text-[#7A2525]" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <span>{error}</span>
              </div>
            )}

            {/* Email Field */}
            <div>
              <label
                htmlFor="email"
                className="block text-xs font-semibold uppercase tracking-wider text-[#6F6A61] mb-1.5"
              >
                Work Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-[#FFFFFF] border border-[#E8E2D8] rounded-xl text-sm text-[#292722] placeholder:text-[#AAA49B] focus:outline-none focus:border-[#756653] focus:ring-1 focus:ring-[#756653] transition-colors"
                placeholder="name@company.com"
                disabled={loading}
              />
            </div>

            {/* Password Field */}
            <div>
              <label
                htmlFor="password"
                className="block text-xs font-semibold uppercase tracking-wider text-[#6F6A61] mb-1.5"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-[#FFFFFF] border border-[#E8E2D8] rounded-xl text-sm text-[#292722] placeholder:text-[#AAA49B] focus:outline-none focus:border-[#756653] focus:ring-1 focus:ring-[#756653] transition-colors"
                placeholder="••••••••••••"
                disabled={loading}
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#756653] hover:bg-[#5F5243] text-[#FAF9F6] py-2.5 px-4 rounded-xl text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-[#756653] focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed transition-colors shadow-2xs mt-2"
            >
              {loading ? "Authenticating…" : "Sign In to Workspace"}
            </button>
          </form>

          {/* Quick Demo Pre-fill helpers */}
          <div className="mt-8 pt-6 border-t border-[#EFEAE2]">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-[#918A80] mb-3 text-center">
              Demo Access Profiles
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => handlePrefill("recruiter@shortlist.ai", "ShortlistAI@2026!")}
                className="text-left px-3 py-2 rounded-lg bg-[#F5F1EA] hover:bg-[#EEE8DD] border border-[#E8E2D8] transition-colors"
              >
                <div className="font-semibold text-[#292722]">Recruiter</div>
                <div className="text-[10px] text-[#6F6A61] truncate">recruiter@shortlist.ai</div>
              </button>
              <button
                type="button"
                onClick={() => handlePrefill("client@acmecorp.com", "ShortlistAI@2026!")}
                className="text-left px-3 py-2 rounded-lg bg-[#F5F1EA] hover:bg-[#EEE8DD] border border-[#E8E2D8] transition-colors"
              >
                <div className="font-semibold text-[#292722]">Client Manager</div>
                <div className="text-[10px] text-[#6F6A61] truncate">client@acmecorp.com</div>
              </button>
              <button
                type="button"
                onClick={() => handlePrefill("delivery@shortlist.ai", "ShortlistAI@2026!")}
                className="text-left px-3 py-2 rounded-lg bg-[#F5F1EA] hover:bg-[#EEE8DD] border border-[#E8E2D8] transition-colors"
              >
                <div className="font-semibold text-[#292722]">Delivery Head</div>
                <div className="text-[10px] text-[#6F6A61] truncate">delivery@shortlist.ai</div>
              </button>
              <button
                type="button"
                onClick={() => handlePrefill("compliance@shortlist.ai", "ShortlistAI@2026!")}
                className="text-left px-3 py-2 rounded-lg bg-[#F5F1EA] hover:bg-[#EEE8DD] border border-[#E8E2D8] transition-colors"
              >
                <div className="font-semibold text-[#292722]">Compliance</div>
                <div className="text-[10px] text-[#6F6A61] truncate">compliance@shortlist.ai</div>
              </button>
            </div>
          </div>
        </div>

        {/* Security & Footer Notice */}
        <div className="mt-8 text-center text-xs text-[#918A80] space-y-1">
          <p>Protected by ShortlistAI Multi-Tenant Enterprise Security</p>
          <p>© {new Date().getFullYear()} ShortlistAI Platform. All rights reserved.</p>
        </div>
      </div>
    </div>
  );
}
