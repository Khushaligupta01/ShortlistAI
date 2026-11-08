"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Briefcase,
  Users,
  Kanban,
  SendHorizontal,
  ShieldCheck,
  Scale,
  TrendingUp,
  FileCheck2,
  LogOut,
  Menu,
  X,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import { clearTokens, getRefreshToken } from "@/lib/auth";
import type { CurrentUser } from "@/lib/types";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface AppShellProps {
  user: CurrentUser | null;
  title?: string;
  subtitle?: string;
  breadcrumbs?: BreadcrumbItem[];
  actions?: React.ReactNode;
  children: React.ReactNode;
}

const roleDisplayMap: Record<string, { label: string; badge: string }> = {
  recruiter: { label: "Recruiter", badge: "Agency Workspace" },
  delivery_head: { label: "Delivery Head", badge: "Executive Oversight" },
  client_hiring_manager: { label: "Client Manager", badge: "Client Portal" },
};

export default function AppShell({
  user,
  title,
  subtitle,
  breadcrumbs = [],
  actions,
  children,
}: AppShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  async function handleLogout() {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      await api.logout(refreshToken).catch(() => null);
    }
    clearTokens();
    router.push("/login");
  }

  const role = user?.role ?? "recruiter";
  const isClient = role === "client_hiring_manager";
  const isDeliveryHead = role === "delivery_head";

  // Build navigation items based on role
  const navItems = isClient
    ? [
        { label: "Dashboard", href: "/client", icon: LayoutDashboard },
        { label: "Shared Requisitions", href: "/client/requisitions", icon: Briefcase },
        { label: "Candidates & Shortlist", href: "/client/submissions", icon: Users },
        { label: "Interview Requests", href: "/client/requests", icon: FileCheck2 },
      ]
    : [
        { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
        { label: "Requisitions", href: "/requisitions", icon: Briefcase },
        { label: "Candidates", href: "/candidates", icon: Users },
        { label: "Hiring Pipeline", href: "/pipeline", icon: Kanban },
        { label: "Client Submissions", href: "/submissions", icon: SendHorizontal },
        { label: "Privacy & Consent", href: "/privacy", icon: ShieldCheck },
        { label: "AI Governance", href: "/governance", icon: Scale },
        ...(isDeliveryHead
          ? [{ label: "Delivery Overview", href: "/delivery", icon: TrendingUp }]
          : []),
      ];

  const roleInfo = roleDisplayMap[role] ?? { label: role, badge: "Workspace" };

  return (
    <div className="min-h-screen bg-[#FAF9F6] text-[#292722] flex flex-col md:flex-row antialiased">
      {/* Mobile Header Bar */}
      <div className="md:hidden flex items-center justify-between px-4 h-15 bg-[#F3EFE8] border-b border-[#E8E2D8] sticky top-0 z-40">
        <Link href={isClient ? "/client" : "/dashboard"} className="flex items-center gap-2">
          <span className="w-7 h-7 rounded-md bg-[#756653] text-[#FAF9F6] font-bold text-sm flex items-center justify-center shadow-xs">
            S
          </span>
          <span className="font-semibold text-base tracking-tight text-[#292722]">ShortlistAI</span>
          <span className="text-[10px] font-semibold bg-[#EDE5D9] text-[#756653] px-2 py-0.5 rounded-full uppercase tracking-wider">
            {isClient ? "Client" : "Recruiter"}
          </span>
        </Link>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-1.5 text-[#6F6A61] hover:text-[#292722] rounded-md hover:bg-[#E8E2D8] transition-colors"
          aria-label="Toggle Navigation"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Sidebar Navigation */}
      <aside
        className={`fixed md:sticky top-0 h-screen w-64 bg-[#F3EFE8] border-r border-[#E8E2D8] flex flex-col z-30 transition-transform duration-200 ease-in-out ${
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 px-6 flex items-center justify-between border-b border-[#E8E2D8]">
          <Link href={isClient ? "/client" : "/dashboard"} className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#756653] text-[#FAF9F6] font-bold text-base flex items-center justify-center shadow-xs">
              S
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-base tracking-tight text-[#292722]">ShortlistAI</span>
                <Sparkles className="w-3.5 h-3.5 text-[#A8957D]" />
              </div>
              <p className="text-[11px] font-medium text-[#6F6A61] -mt-0.5">{roleInfo.badge}</p>
            </div>
          </Link>
        </div>

        {/* Navigation List */}
        <div className="flex-1 px-3 py-4 overflow-y-auto space-y-1">
          <p className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-[#918A80]">
            Navigation
          </p>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/dashboard" || item.href === "/client"
                ? pathname === item.href
                : pathname?.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? "bg-[#EDE5D9] text-[#292722] font-semibold shadow-2xs border border-[#E8E2D8]"
                    : "text-[#6F6A61] hover:text-[#292722] hover:bg-[#EFEAE2]"
                }`}
              >
                <Icon
                  className={`w-4 h-4 transition-colors ${
                    isActive ? "text-[#756653]" : "text-[#918A80]"
                  }`}
                />
                <span className="flex-1">{item.label}</span>
                {isActive && <div className="w-1.5 h-1.5 rounded-full bg-[#756653]" />}
              </Link>
            );
          })}
        </div>

        {/* User Profile & Sign Out Footer */}
        <div className="p-3 border-t border-[#E8E2D8] bg-[#EEE8DD]/50">
          <div className="p-2.5 rounded-lg bg-[#FFFFFF] border border-[#E8E2D8] shadow-2xs mb-2">
            <div className="flex items-center justify-between">
              <div className="truncate pr-2">
                <p className="text-xs font-semibold text-[#292722] truncate">
                  {user?.display_name || user?.email || "Authenticated User"}
                </p>
                <p className="text-[11px] text-[#6F6A61] truncate">{user?.email}</p>
              </div>
              <span className="text-[10px] font-semibold bg-[#EDE5D9] text-[#756653] px-1.5 py-0.5 rounded uppercase tracking-wider shrink-0">
                {roleInfo.label}
              </span>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold text-[#6F6A61] hover:text-[#292722] hover:bg-[#E8E2D8] transition-colors border border-transparent hover:border-[#D9D1C5]"
          >
            <LogOut className="w-3.5 h-3.5 text-[#918A80]" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Workspace Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Workspace Top Header Bar */}
        <header className="h-16 px-6 lg:px-8 bg-[#FFFFFF] border-b border-[#E8E2D8] flex items-center justify-between sticky top-0 z-20 shadow-2xs">
          {/* Left: Breadcrumbs & Title */}
          <div>
            {breadcrumbs.length > 0 && (
              <nav className="flex items-center gap-1 text-[11px] text-[#6F6A61] mb-0.5">
                <Link href={isClient ? "/client" : "/dashboard"} className="hover:text-[#292722]">
                  {isClient ? "Client Portal" : "Recruiter"}
                </Link>
                {breadcrumbs.map((bc, idx) => (
                  <React.Fragment key={idx}>
                    <ChevronRight className="w-3 h-3 text-[#AAA49B]" />
                    {bc.href ? (
                      <Link href={bc.href} className="hover:text-[#292722]">
                        {bc.label}
                      </Link>
                    ) : (
                      <span className="text-[#292722] font-medium">{bc.label}</span>
                    )}
                  </React.Fragment>
                ))}
              </nav>
            )}
            <h1 className="text-lg lg:text-xl font-bold tracking-tight text-[#292722]">
              {title || "Overview"}
            </h1>
          </div>

          {/* Right: Actions */}
          {actions && <div className="flex items-center gap-3">{actions}</div>}
        </header>

        {/* Content Body */}
        <main className="flex-1 p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6">
          {subtitle && (
            <div className="pb-2 border-b border-[#EFEAE2]">
              <p className="text-sm text-[#6F6A61]">{subtitle}</p>
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}

