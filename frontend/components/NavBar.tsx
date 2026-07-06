"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { MenuDrawer } from "@/components/MenuDrawer";
import { SearchIcon } from "@/components/icons";

const LINKS = [
  { href: "/", label: "Games" },
  { href: "/shorts", label: "Shorts" },
  { href: "/community", label: "Community" },
  { href: "/chat", label: "Chat" },
  { href: "/messages", label: "Messages" },
  { href: "/ide", label: "IDE" },
];

export function NavBar() {
  const { user, loading } = useAuth();
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-10 border-b border-neutral-800 bg-neutral-900/80 backdrop-blur">
      <nav className="mx-auto flex h-14 max-w-4xl items-center gap-2 px-4">
        <Link href="/" className="shrink-0 text-lg font-bold tracking-tight">
          Play<span className="text-indigo-500">hub</span>
        </Link>

        {user && (
          <div className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto text-sm">
            {LINKS.slice(1).map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`shrink-0 rounded-md px-3 py-1.5 hover:bg-neutral-800 ${
                  pathname === l.href ? "text-indigo-400" : "text-neutral-300"
                }`}
              >
                {l.label}
              </Link>
            ))}
          </div>
        )}

        <div className="ml-auto flex shrink-0 items-center gap-2 text-sm">
          {loading ? null : user ? (
            <>
              <SearchBox />
              <Link
                href="/upload"
                className="hidden sm:block rounded-md border border-neutral-700 px-3 py-1.5 hover:bg-neutral-800"
              >
                Upload
              </Link>
              <Link href={`/u/${user.username}`} className="flex items-center gap-2 hover:opacity-80">
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-indigo-500 text-xs font-semibold text-white">
                  {user.username.slice(0, 2).toUpperCase()}
                </span>
              </Link>
              <MenuDrawer />
            </>
          ) : (
            <>
              <Link href="/login" className="rounded-md px-3 py-1.5 hover:bg-neutral-800">
                Log in
              </Link>
              <Link href="/register" className="rounded-md bg-indigo-500 px-3 py-1.5 font-medium text-white hover:bg-indigo-600">
                Sign up
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}

function SearchBox() {
  const router = useRouter();
  const [q, setQ] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const t = q.trim();
    if (t) router.push(`/search?q=${encodeURIComponent(t)}`);
  }

  return (
    <>
      {/* Desktop: inline search box */}
      <form onSubmit={submit} className="hidden md:block">
        <div className="relative">
          <SearchIcon className="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="게임 · 게시물 · 유저 검색"
            className="w-44 rounded-md border border-neutral-700 bg-neutral-800/60 py-1.5 pl-8 pr-3 text-sm outline-none focus:border-indigo-500 lg:w-60"
          />
        </div>
      </form>
      {/* Mobile: search icon → search page */}
      <Link
        href="/search"
        aria-label="검색"
        className="rounded-md p-1.5 text-neutral-300 hover:bg-neutral-800 md:hidden"
      >
        <SearchIcon className="h-5 w-5" />
      </Link>
    </>
  );
}
