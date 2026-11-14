import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "올림픽공원 공연 추천",
    short_name: "공연 추천",
    description: "올림픽공원 공연을 취향·날짜에 맞춰 추천합니다.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    lang: "ko",
    background_color: "#f7faf8",
    theme_color: "#237034",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512-maskable.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
