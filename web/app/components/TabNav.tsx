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
    <nav className="border-b border-zinc-800 bg-zinc-950">
      <div className="max-w-5xl mx-auto px-4 flex gap-0">
        {TABS.map((tab) => {
          const active = path.startsWith(tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                active
                  ? "border-red-500 text-white"
                  : "border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
