"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/race",      label: "Race Weekend" },
  { href: "/record",   label: "Season Record" },
  { href: "/portfolio", label: "Portfolio" },
];

export function TabNav() {
  const path = usePathname();
  return (
    <nav style={{ borderBottom: "1px solid #1F1F23", background: "#100D0B" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 32px", display: "flex", gap: 28 }}>
        {TABS.map((tab) => {
          const active = path.startsWith(tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              style={{
                padding: "12px 2px",
                fontSize: 14,
                fontWeight: active ? 500 : 400,
                color: active ? "#FAFAFA" : "#A1A1AA",
                borderBottom: active ? "2px solid #E8002D" : "2px solid transparent",
                marginBottom: -1,
                letterSpacing: "-0.005em",
                textDecoration: "none",
                display: "block",
              }}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
