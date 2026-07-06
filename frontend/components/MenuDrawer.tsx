"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  ActivityIcon,
  BellIcon,
  BookmarkIcon,
  ClockIcon,
  CommentIcon,
  EyeIcon,
  GearIcon,
  ImageIcon,
  LogoutIcon,
  MenuIcon,
  PlusIcon,
  ShieldIcon,
  StarIcon,
  UsersIcon,
  XIcon,
} from "@/components/icons";

type Item = { href: string; label: string; sub: string; icon: React.ReactNode };

const ITEMS: Item[] = [
  { href: "/saved", label: "저장", sub: "저장한 게임", icon: <BookmarkIcon className="h-5 w-5" /> },
  { href: "/menu/dm-media", label: "DM 자료", sub: "DM으로 주고받은 이미지·파일", icon: <ImageIcon className="h-5 w-5" /> },
  { href: "/menu/profile", label: "프로필 수정", sub: "이름·소개·아바타", icon: <GearIcon className="h-5 w-5" /> },
  { href: "/menu/friends", label: "친구 관리", sub: "팔로워·팔로잉·요청", icon: <UsersIcon className="h-5 w-5" /> },
  { href: "/menu/activity", label: "나의 활동", sub: "게임·글·좋아요 요약", icon: <ActivityIcon className="h-5 w-5" /> },
  { href: "/menu/notifications", label: "알림", sub: "받은 알림 자세히", icon: <BellIcon className="h-5 w-5" /> },
  { href: "/menu/activity-time", label: "활동 시간", sub: "가입일·최근 접속", icon: <ClockIcon className="h-5 w-5" /> },
  { href: "/menu/privacy", label: "공개 범위", sub: "계정 공개 설정", icon: <EyeIcon className="h-5 w-5" /> },
  { href: "/menu/safety", label: "차단 및 신고", sub: "차단 목록·신고", icon: <ShieldIcon className="h-5 w-5" /> },
  { href: "/menu/comments", label: "댓글", sub: "내가 남긴 댓글", icon: <CommentIcon className="h-5 w-5" /> },
  { href: "/menu/favorites", label: "즐겨찾기", sub: "좋아요한 게임·글", icon: <StarIcon className="h-5 w-5" /> },
];

export function MenuDrawer() {
  const { user, accounts, switchAccount, removeAccount, logout } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  // Lock body scroll while the drawer is open.
  useEffect(() => {
    if (open) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [open]);

  if (!user) return null;

  function go(href: string) {
    setOpen(false);
    router.push(href);
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        aria-label="Menu"
        className="rounded-md p-1.5 text-neutral-300 hover:bg-neutral-800"
      >
        <MenuIcon className="h-5 w-5" />
      </button>

      {open && typeof document !== "undefined" && createPortal(
        // Portaled to <body> so the fixed overlay escapes the NavBar's
        // backdrop-blur, which otherwise becomes the containing block and clips it.
        <div className="fixed inset-0 z-[100]">
          <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} />
          <aside className="absolute right-0 top-0 flex h-full w-80 max-w-[85vw] flex-col border-l border-neutral-800 bg-neutral-950 shadow-xl">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-neutral-800 px-4 py-3">
              <span className="font-semibold">메뉴</span>
              <button onClick={() => setOpen(false)} className="rounded-md p-1 text-neutral-400 hover:bg-neutral-800">
                <XIcon className="h-5 w-5" />
              </button>
            </div>

            {/* Items */}
            <nav className="min-h-0 flex-1 overflow-y-auto py-2">
              {ITEMS.map((it) => (
                <button
                  key={it.href}
                  onClick={() => go(it.href)}
                  className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-neutral-800/60"
                >
                  <span className="text-neutral-400">{it.icon}</span>
                  <span className="min-w-0">
                    <span className="block text-sm text-neutral-100">{it.label}</span>
                    <span className="block truncate text-xs text-neutral-500">{it.sub}</span>
                  </span>
                </button>
              ))}

              {/* 12. 계정 상태 */}
              <div className="mt-2 border-t border-neutral-800 px-4 pt-3 pb-2">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">계정 상태</p>
                <div className="mb-2 flex items-center gap-3 rounded-lg bg-neutral-900 px-3 py-2">
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500 text-xs font-semibold text-white">
                    {user.username.slice(0, 2).toUpperCase()}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm">{user.display_name || user.username}</span>
                    <span className="block truncate text-xs text-neutral-500">@{user.username}</span>
                  </span>
                </div>

                {accounts.filter((a) => a.username !== user.username).map((a) => (
                  <div key={a.username} className="flex items-center gap-2 rounded-lg px-1 py-1">
                    <button
                      onClick={() => { setOpen(false); switchAccount(a.username); }}
                      className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-neutral-800"
                    >
                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-neutral-700 text-[10px] font-semibold">
                        {a.username.slice(0, 2).toUpperCase()}
                      </span>
                      <span className="truncate text-sm text-neutral-300">@{a.username} 로 전환</span>
                    </button>
                    <button
                      onClick={() => removeAccount(a.username)}
                      className="rounded-md p-1 text-neutral-600 hover:text-red-400"
                      title="이 계정 제거"
                    >
                      <XIcon className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}

                <button
                  onClick={() => go("/login")}
                  className="mt-1 flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm text-neutral-300 hover:bg-neutral-800"
                >
                  <PlusIcon className="h-4 w-4" /> 계정 추가
                </button>
                <button
                  onClick={() => { setOpen(false); logout(); router.push("/login"); }}
                  className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm text-red-400 hover:bg-neutral-800"
                >
                  <LogoutIcon className="h-4 w-4" /> 로그아웃
                </button>
              </div>
            </nav>
          </aside>
        </div>,
        document.body,
      )}
    </>
  );
}
