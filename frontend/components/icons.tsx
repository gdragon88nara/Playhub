// Minimal inline SVG icons (no emoji anywhere in the app).
import type { SVGProps } from "react";

type P = SVGProps<SVGSVGElement> & { filled?: boolean };

const base = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function PlayIcon({ filled, ...p }: P) {
  return (
    <svg {...base} fill={filled ? "currentColor" : "none"} {...p}>
      <path d="M6 4.5v15l13-7.5-13-7.5Z" />
    </svg>
  );
}

export function HeartIcon({ filled, ...p }: P) {
  return (
    <svg {...base} fill={filled ? "currentColor" : "none"} {...p}>
      <path d="M12 20s-7-4.35-9.5-8.5C1 8.5 2.5 5.5 6 5.5c2 0 3 1 4 2.5 1-1.5 2-2.5 4-2.5 3.5 0 5 3 3.5 6C19 15.65 12 20 12 20Z" />
    </svg>
  );
}

export function CommentIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M21 12a8 8 0 0 1-11.5 7.2L4 20l1-4.5A8 8 0 1 1 21 12Z" />
    </svg>
  );
}

export function BookmarkIcon({ filled, ...p }: P) {
  return (
    <svg {...base} fill={filled ? "currentColor" : "none"} {...p}>
      <path d="M6 4h12v16l-6-4-6 4V4Z" />
    </svg>
  );
}

export function LockIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </svg>
  );
}

export function PlusIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function MessageIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M4 5h16v11H8l-4 4V5Z" />
    </svg>
  );
}

export function GamepadIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M7 11h4M9 9v4M15 10h.01M18 12h.01" />
      <rect x="2" y="6" width="20" height="12" rx="4" />
    </svg>
  );
}

export function FilmIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 9h18M3 15h18M8 4v16M16 4v16" />
    </svg>
  );
}

export function FilesIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6Z" />
      <path d="M14 3v6h6" />
    </svg>
  );
}

export function MonitorIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <rect x="3" y="4" width="18" height="12" rx="2" />
      <path d="M8 20h8M12 16v4" />
    </svg>
  );
}

export function TerminalIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M7 9l3 3-3 3M13 15h4" />
    </svg>
  );
}

export function RocketIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M5 15c-1 1-1.5 4-1.5 4s3-.5 4-1.5a2.12 2.12 0 0 0-2.5-2.5Z" />
      <path d="M9 15l-3-3a12 12 0 0 1 9-9c2 0 3 1 3 3a12 12 0 0 1-9 9Z" />
      <path d="M14 8h.01" />
    </svg>
  );
}

export function RefreshIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M4 12a8 8 0 0 1 14-5l2 2M20 12a8 8 0 0 1-14 5l-2-2M18 4v5h-5M6 20v-5h5" />
    </svg>
  );
}

export function XIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

export function UploadIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M12 15V3m0 0L8 7m4-4 4 4" />
      <path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4" />
    </svg>
  );
}

export function FolderIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" />
    </svg>
  );
}

export function MenuIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

export function BellIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M6 9a6 6 0 0 1 12 0c0 4 1 5 2 6H4c1-1 2-2 2-6Z" />
      <path d="M10 20a2 2 0 0 0 4 0" />
    </svg>
  );
}

export function ClockIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v4l3 2" />
    </svg>
  );
}

export function ShieldIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6l7-3Z" />
    </svg>
  );
}

export function StarIcon({ filled, ...p }: P) {
  return (
    <svg {...base} fill={filled ? "currentColor" : "none"} {...p}>
      <path d="M12 3l2.7 5.5 6 .9-4.3 4.2 1 6-5.4-2.8-5.4 2.8 1-6L3.3 9.4l6-.9L12 3Z" />
    </svg>
  );
}

export function GearIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-2.9 1.2V21a2 2 0 1 1-4 0v-.1A1.7 1.7 0 0 0 6.2 19l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0-1.2-2.9H2a2 2 0 1 1 0-4h.1A1.7 1.7 0 0 0 3.3 6.2l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H8a1.7 1.7 0 0 0 1-1.5V2a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 2.9 1.2l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V8a1.7 1.7 0 0 0 1.5 1H22a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" />
    </svg>
  );
}

export function UsersIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M16 20v-1a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v1" />
      <circle cx="9" cy="8" r="3.5" />
      <path d="M22 20v-1a4 4 0 0 0-3-3.9M16 4.2a3.5 3.5 0 0 1 0 6.8" />
    </svg>
  );
}

export function ActivityIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M3 12h4l3 8 4-16 3 8h4" />
    </svg>
  );
}

export function LogoutIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" />
      <path d="M10 17l-5-5 5-5M15 12H5" />
    </svg>
  );
}

export function ImageIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <circle cx="9" cy="10" r="2" />
      <path d="M21 16l-5-5-6 6" />
    </svg>
  );
}

export function SearchIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3" />
    </svg>
  );
}

export function MaximizeIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" />
    </svg>
  );
}

export function EyeIcon(p: P) {
  return (
    <svg {...base} {...p}>
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}
