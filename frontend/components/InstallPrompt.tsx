"use client";

import { useEffect, useState } from "react";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

function isIos(): boolean {
  return typeof navigator !== "undefined" && /iphone|ipad|ipod/i.test(navigator.userAgent);
}

function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  const nav = navigator as Navigator & { standalone?: boolean };
  return window.matchMedia("(display-mode: standalone)").matches || nav.standalone === true;
}

function wasDismissed(): boolean {
  return typeof window !== "undefined" && sessionStorage.getItem("install-prompt-dismissed") === "1";
}

/** QR로 처음 들어온 화면에서 바로 보이는 설치 유도 배너.
 * Android/Chrome 계열은 `beforeinstallprompt`로 한 번에 설치되지만, iOS Safari는
 * Apple이 이 API 자체를 막아놔서 "공유 → 홈 화면에 추가" 수동 안내만 가능하다. */
export default function InstallPrompt() {
  const [dismissed, setDismissed] = useState(() => isStandalone() || wasDismissed());
  const [showIosHint] = useState(() => !isStandalone() && !wasDismissed() && isIos());
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    if (dismissed || showIosHint) return;
    function onBeforeInstallPrompt(e: Event) {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    }
    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
  }, [dismissed, showIosHint]);

  function dismiss() {
    setDismissed(true);
    sessionStorage.setItem("install-prompt-dismissed", "1");
  }

  async function install() {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    setDeferredPrompt(null);
  }

  if (dismissed || (!deferredPrompt && !showIosHint)) return null;

  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-line bg-surface-2 px-3 py-2">
      <p className="text-xs text-foreground">
        {deferredPrompt
          ? "앱으로 설치하면 더 빠르게 쓸 수 있어요."
          : "공유 버튼을 누르고 '홈 화면에 추가'하면 앱처럼 쓸 수 있어요."}
      </p>
      <div className="flex shrink-0 items-center gap-2">
        {deferredPrompt && (
          <button
            type="button"
            onClick={install}
            className="rounded-md bg-brand px-2.5 py-1 text-xs font-semibold text-background"
          >
            앱 설치하기
          </button>
        )}
        <button type="button" onClick={dismiss} aria-label="닫기" className="text-muted">
          ✕
        </button>
      </div>
    </div>
  );
}
