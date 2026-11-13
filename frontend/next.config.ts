import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* create-next-app이 기본으로 켜둔 실험적 "Cache Components"/"Partial Prefetching"은
   * 8주 MVP에 꼭 필요하지 않아서 껐다. */

  /* Next.js 16은 기본적으로 127.0.0.1을 통한 dev 리소스(HMR, 청크) 요청을 보안상
   * 차단한다 — "allowedDevOrigins"에 없는 호스트로 접근하면 클라이언트 JS가 제대로
   * 안 돌아서(useEffect가 아예 실행 안 됨) 겉보기엔 "로딩 중"에 멈춘 것처럼 보이는
   * 버그를 겪었다(tasks/verification.md [2026-11-12] 참고). 127.0.0.1로 접근할 일이
   * 있으면(테스트 자동화 등) 허용해야 한다. */
  allowedDevOrigins: ["127.0.0.1", "localhost"],

  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
