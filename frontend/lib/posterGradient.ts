/**
 * 포스터 이미지가 없는 공연을 위한 대체 그라데이션.
 * 올림픽공원 심볼마크(심볼링) 색상에서 추출한 브랜드 팔레트 기반.
 * 같은 공연은 항상 같은 조합이 나오도록 제목을 시드로 결정적으로 선택한다.
 */
const GRADIENT_PAIRS: [string, string][] = [
  ["#1f5e49", "#3c9b47"],
  ["#16a06a", "#2bb8d8"],
  ["#3c9b47", "#c3d62e"],
  ["#157f99", "#3c9b47"],
  ["#2b6b53", "#16a06a"],
];

export function posterGradient(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  const [from, to] = GRADIENT_PAIRS[hash % GRADIENT_PAIRS.length];
  return `linear-gradient(135deg, ${from}, ${to})`;
}
