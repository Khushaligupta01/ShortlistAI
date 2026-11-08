"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Check, Copy } from "lucide-react";
import { api } from "@/lib/api";
import { saveTokens } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("recruiter@techrecruit.com");
  const [password, setPassword] = useState("Recruiter@Demo2024!");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copiedRole, setCopiedRole] = useState<string | null>(null);

  const demoAccounts = [
    {
      role: "Recruiter",
      label: "Full Recruiter Workspace",
      email: "recruiter@techrecruit.com",
      password: "Recruiter@Demo2024!",
      route: "/dashboard",
    },
    {
      role: "Client Manager",
      label: "Client Hiring Portal",
      email: "client@acme.com",
      password: "Client@Demo2024!",
      route: "/client",
    },
    {
      role: "Delivery Head",
      label: "Executive Pipeline",
      email: "head@techrecruit.com",
      password: "Delivery@Demo2024!",
      route: "/delivery",
    },
    {
      role: "Super Admin",
      label: "Privacy & Governance",
      email: "compliance@shortlist.ai",
      password: "ShortlistAI@2026!",
      route: "/privacy",
    },
  ];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const cleanEmail = email.trim();
      const cleanPass = password.trim();
      const tokens = await api.login(cleanEmail, cleanPass);
      saveTokens(tokens);

      // Determine where to redirect based on role
      const user = await api.getCurrentUser();
      if (user.role === "client_hiring_manager") {
        router.push("/client");
      } else {
        router.push("/dashboard");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication failed. Please verify credentials.");
    } finally {
      setLoading(false);
    }
  }

  function handlePrefill(acc: typeof demoAccounts[0]) {
    setEmail(acc.email);
    setPassword(acc.password);
    setError(null);
    setCopiedRole(acc.role);
    setTimeout(() => setCopiedRole(null), 1500);
  }

  return (
    <div className="min-h-screen bg-[#FAF9F6] flex flex-col items-center justify-center px-4 py-12 selection:bg-[#EDE5D9] selection:text-[#292722]">
      <div className="w-full max-w-md">
        {/* Logo / Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#756653] text-[#FAF9F6] text-xl font-serif font-bold shadow-sm mb-3">
            S
          </div>
          <h1 className="text-2xl font-serif font-bold tracking-tight text-[#292722]">
            ShortlistAI
          </h1>
          <p className="text-sm text-[#6F6A61] mt-1">
            Evidence-based AI resume screening & client shortlist platform
          </p>
        </div>

        {/* Elevated Login Card */}
        <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] shadow-sm p-8 sm:p-9 transition-all">
          <div className="mb-6">
            <h2 className="text-lg font-serif font-bold text-[#292722]">
              Sign in to your account
            </h2>
            <p className="text-xs text-[#918A80] mt-0.5">
              Select a demo profile below or enter corporate credentials
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
                Work Email / Username
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-[#FAF9F6] border border-[#D9D1C5] rounded-xl text-sm text-[#292722] placeholder:text-[#AAA49B] focus:outline-none focus:ring-2 focus:ring-[#756653] transition-colors"
                placeholder="name@company.com"
                disabled={loading}
              />
            </div>

            {/* Password Field with Show/Hide Toggle */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  htmlFor="password"
                  className="block text-xs font-semibold uppercase tracking-wider text-[#6F6A61]"
                >
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-[11px] text-[#756653] hover:text-[#292722] inline-flex items-center gap-1 transition"
                >
                  {showPassword ? (
                    <>
                      <EyeOff className="w-3.5 h-3.5" /> Hide
                    </>
                  ) : (
                    <>
                      <Eye className="w-3.5 h-3.5" /> Show
                    </>
                  )}
                </button>
              </div>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3.5 py-2.5 pr-10 bg-[#FAF9F6] border border-[#D9D1C5] rounded-xl text-sm text-[#292722] placeholder:text-[#AAA49B] focus:outline-none focus:ring-2 focus:ring-[#756653] transition-colors font-mono"
                  placeholder="••••••••••••"
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3 text-[#918A80] hover:text-[#292722]"
                  title={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#756653] hover:bg-[#5F5243] text-white py-2.5 px-4 rounded-xl text-sm font-bold focus:outline-none focus:ring-2 focus:ring-[#756653] focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed transition-colors shadow-sm mt-2"
            >
              {loading ? "Authenticating…" : "Sign In to Workspace"}
            </button>
          </form>

          {/* Quick Demo Pre-fill helpers */}
          <div className="mt-8 pt-6 border-t border-[#EFEAE2]">
            <div className="flex items-center justify-between mb-3">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-[#918A80]">
                Click Any Demo Profile to Auto-Fill:
              </p>
              {copiedRole && (
                <span className="text-[11px] font-semibold text-[#2A5A35] flex items-center gap-1">
                  <Check className="w-3 h-3" /> Filled {copiedRole}!
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              {demoAccounts.map((acc) => {
                const isSelected = email === acc.email;
                return (
                  <button
                    key={acc.role}
                    type="button"
                    onClick={() => handlePrefill(acc)}
                    className={`text-left p-2.5 rounded-xl border transition-all ${
                      isSelected
                        ? "bg-[#EDE5D9] border-[#756653] text-[#292722] shadow-xs"
                        : "bg-[#F5F1EA] hover:bg-[#EEE8DD] border-[#E8E2D8] text-[#292722]"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold">{acc.role}</span>
                      {isSelected ? (
                        <span className="w-2 h-2 rounded-full bg-[#756653]" />
                      ) : (
                        <Copy className="w-3 h-3 text-[#918A80]" />
                      )}
                    </div>
                    <div className="text-[11px] text-[#6F6A61] truncate mt-0.5 font-mono">{acc.email}</div>
                    <div className="text-[10px] text-[#918A80] truncate font-mono mt-0.5">Key: {acc.password}</div>
                  </button>
                );
              })}
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
