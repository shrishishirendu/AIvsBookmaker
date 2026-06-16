"use client";

import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/leaderboard", label: "Leaderboard" },
  { href: "/highlights", label: "Highlights" },
  { href: "/play", label: "Play" },
  { href: "/admin", label: "Admin" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <nav className="sticky top-0 z-20 border-b border-neutral-800 bg-neutral-950/80 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-1 px-6 py-3">
        <a href="/" className="mr-4 text-sm font-black tracking-tight">
          <span className="text-emerald-400">⚔</span> Disagreement Engine
        </a>
        {LINKS.map((l) => {
          const active = l.href === "/" ? path === "/" : path.startsWith(l.href);
          return (
            <a
              key={l.href}
              href={l.href}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                active ? "bg-neutral-800 text-white" : "text-neutral-400 hover:text-white"
              }`}
            >
              {l.label}
            </a>
          );
        })}
      </div>
    </nav>
  );
}
