// bzzorio image proxy — https://sports.bzzoiro.com/docs/images/
// Public, unauthenticated, hotlink-friendly. Server/edge-cached up to 30 days,
// and served with Cache-Control: public, max-age=31536000, so the browser's
// own HTTP cache already does the heavy lifting once an id has been fetched
// once. A valid id with no image responds 204 (not 404), so there is no
// guaranteed non-empty image to fall back to — the client has to render its
// own placeholder for that case.
const IMAGE_BASE = "https://sports.bzzoiro.com/img";

export function teamLogoUrl(teamId: number): string {
  return `${IMAGE_BASE}/team/${teamId}/?bg=transparent`;
}

export function leagueLogoUrl(leagueId: number): string {
  return `${IMAGE_BASE}/league/${leagueId}/?bg=transparent`;
}
