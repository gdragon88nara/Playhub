"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

// Shared guard + frame for every account-menu page.
export default function MenuLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  if (loading) return <p className="text-neutral-500">Loading…</p>;
  if (!user) return null;
  return <div className="space-y-5">{children}</div>;
}
