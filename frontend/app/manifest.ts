import type { MetadataRoute } from "next";

// Web App Manifest — Next serves this at /manifest.webmanifest and links it
// automatically, making the app installable to the home screen.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Playhub — Game Platform",
    short_name: "Playhub",
    description: "Upload and play games. Follow creators. Build together.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "any",
    background_color: "#0a0a0a",
    theme_color: "#6366f1",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "maskable" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
