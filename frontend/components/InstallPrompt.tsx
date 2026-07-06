"use client";

import { useEffect, useState } from "react";
import { XIcon } from "@/components/icons";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

// Registers the service worker and shows an install banner whenever the app is
// installable (Chromium/Android) or on iOS Safari (manual Add-to-Home-Screen).
// It reappears on every fresh load — including first visit and login — until the
// app is installed. Auto-hides when already running as an installed app.
export function InstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [show, setShow] = useState(false);
  const [ios, setIos] = useState(false);

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }

    const standalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      (window.navigator as unknown as { standalone?: boolean }).standalone === true;
    if (standalone) return; // already installed

    const ua = window.navigator.userAgent;
    const isIOS = /iphone|ipad|ipod/i.test(ua);
    const isSafari = /safari/i.test(ua) && !/crios|fxios|chrome/i.test(ua);

    const onBIP = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
      setShow(true);
    };
    const onInstalled = () => setShow(false);
    window.addEventListener("beforeinstallprompt", onBIP);
    window.addEventListener("appinstalled", onInstalled);

    if (isIOS && isSafari) {
      setIos(true);
      setShow(true);
    }

    return () => {
      window.removeEventListener("beforeinstallprompt", onBIP);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  async function install() {
    if (!deferred) return;
    await deferred.prompt();
    await deferred.userChoice;
    setDeferred(null);
    setShow(false);
  }

  if (!show) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-[90] flex justify-center px-4 pb-[calc(env(safe-area-inset-bottom)_+_1rem)]">
      <div className="flex w-full max-w-md items-center gap-3 rounded-2xl border border-neutral-700 bg-neutral-900/95 p-3 shadow-2xl backdrop-blur">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/icon-192.png" alt="" className="h-11 w-11 shrink-0 rounded-xl" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-neutral-100">앱 설치</p>
          <p className="truncate text-xs text-neutral-400">
            {ios ? "공유 → '홈 화면에 추가'로 설치" : "홈 화면에 Playhub를 설치하세요"}
          </p>
        </div>
        {!ios && (
          <button
            onClick={install}
            className="shrink-0 rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600"
          >
            설치
          </button>
        )}
        <button
          onClick={() => setShow(false)}
          aria-label="닫기"
          className="shrink-0 rounded-md p-1 text-neutral-500 hover:text-neutral-200"
        >
          <XIcon className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
