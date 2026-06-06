"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Building2, Columns3, Home, Inbox, Settings, Sparkles } from "lucide-react";

const items = [
  { href: "/", label: "Home", icon: Home },
  { href: "/filings", label: "Filings", icon: Columns3 },
  { href: "/actions", label: "Action Center", icon: Inbox },
  { href: "/profile", label: "Company Profile", icon: Building2 },
  { href: "/activity", label: "Activity", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <Link className="brand" href="/">
        <div className="brand-mark">
          <Sparkles size={22} />
        </div>
        <div>
          <h1>PortalPilot</h1>
          <span>Filing agents</span>
        </div>
      </Link>
      <nav className="nav">
        {items.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link className={active ? "active" : ""} href={item.href} key={item.href}>
              <Icon size={18} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
