// Thin API client for the Django backend with JWT handling + auto refresh.

// API origin. Empty string = same-origin (single-service deploy: the API is
// served under the same host as the app, so calls are relative). A bare host
// (no scheme) is upgraded to https. Undefined falls back to the local dev API.
const RAW_API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const API_BASE =
  RAW_API_BASE && !/^https?:\/\//.test(RAW_API_BASE)
    ? `https://${RAW_API_BASE}`
    : RAW_API_BASE;

const ACCESS_KEY = "gp_access";
const REFRESH_KEY = "gp_refresh";

export const tokens = {
  get access() {
    return typeof window === "undefined" ? null : localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return typeof window === "undefined" ? null : localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

// Multi-account: remember signed-in accounts locally so the user can switch
// between them without re-entering a password each time.
const ACCOUNTS_KEY = "gp_accounts";

export interface SavedAccount {
  username: string;
  display_name: string;
  access: string;
  refresh: string;
}

export const savedAccounts = {
  list(): SavedAccount[] {
    if (typeof window === "undefined") return [];
    try {
      return JSON.parse(localStorage.getItem(ACCOUNTS_KEY) || "[]");
    } catch {
      return [];
    }
  },
  upsert(acc: SavedAccount) {
    const rest = savedAccounts.list().filter((a) => a.username !== acc.username);
    localStorage.setItem(ACCOUNTS_KEY, JSON.stringify([acc, ...rest]));
  },
  remove(username: string) {
    localStorage.setItem(
      ACCOUNTS_KEY,
      JSON.stringify(savedAccounts.list().filter((a) => a.username !== username)),
    );
  },
};

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, data: unknown) {
    super(`API ${status}`);
    this.status = status;
    this.data = data;
  }
}

async function raw(path: string, init: RequestInit = {}, withAuth = true): Promise<Response> {
  const headers = new Headers(init.headers);
  // Never set a JSON content-type for FormData — the browser adds the multipart
  // boundary itself.
  const isForm = init.body instanceof FormData;
  if (!isForm && !headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  if (withAuth && tokens.access) {
    headers.set("Authorization", `Bearer ${tokens.access}`);
  }
  // credentials:"include" lets the signed play/media cookies round-trip so
  // games and private media serve only inside the site.
  return fetch(`${API_BASE}${path}`, { ...init, headers, credentials: "include" });
}

async function refreshAccess(): Promise<boolean> {
  if (!tokens.refresh) return false;
  const res = await raw(
    "/api/auth/refresh",
    { method: "POST", body: JSON.stringify({ refresh: tokens.refresh }) },
    false,
  );
  if (!res.ok) {
    tokens.clear();
    return false;
  }
  const data = await res.json();
  tokens.set(data.access, data.refresh);
  return true;
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit = {},
  withAuth = true,
): Promise<T> {
  let res = await raw(path, init, withAuth);

  // Transparently retry once after refreshing an expired access token.
  if (res.status === 401 && withAuth && tokens.refresh) {
    if (await refreshAccess()) {
      res = await raw(path, init, withAuth);
    }
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

// ---- typed helpers ----------------------------------------------------------

export interface Me {
  id: number;
  email: string;
  username: string;
  display_name: string;
  bio: string;
  avatar: string | null;
  is_private: boolean;
  is_seller: boolean;
  date_joined: string;
  last_active: string | null;
  notify_follows: boolean;
  notify_likes: boolean;
  notify_comments: boolean;
}

export interface PublicUser {
  id: number;
  username: string;
  display_name: string;
  bio: string;
  avatar: string | null;
  is_private: boolean;
  is_seller: boolean;
  followers_count: number;
  following_count: number;
  is_followed_by_me: boolean;
  follow_status?: "self" | "following" | "requested" | "none";
}

export const authApi = {
  async register(body: {
    email: string;
    username: string;
    password: string;
    display_name?: string;
    is_private?: boolean;
    become_seller?: boolean;
  }) {
    return api<Me>("/api/auth/register", { method: "POST", body: JSON.stringify(body) }, false);
  },
  async login(email: string, password: string) {
    const data = await api<{ access: string; refresh: string }>(
      "/api/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
      false,
    );
    tokens.set(data.access, data.refresh);
    return data;
  },
  logout() {
    tokens.clear();
  },
  me() {
    return api<Me>("/api/me");
  },
};

export const usersApi = {
  get(username: string) {
    return api<PublicUser>(`/api/users/${username}`);
  },
  follow(username: string) {
    return api<{ status: string }>(`/api/users/${username}/follow`, { method: "POST" });
  },
  unfollow(username: string) {
    return api(`/api/users/${username}/follow`, { method: "DELETE" });
  },
};

// ---- account menu (hamburger hub) -------------------------------------------

export interface ActivitySummary {
  games: number;
  posts: number;
  comments: number;
  likes_given: number;
  likes_received: number;
  followers: number;
  following: number;
  member_since: string;
  last_active: string | null;
}

export interface Notification {
  id: string;
  type: "follow_request" | "follow" | "like" | "comment";
  actor: { username: string; display_name: string };
  text: string;
  url: string;
  created_at: string;
}

export interface MyComment {
  id: string;
  kind: "game" | "post";
  body: string;
  target: string;
  url: string;
  created_at: string;
}

export interface FollowRequestItem {
  id: number;
  requester: PublicUser;
  status: string;
  created_at: string;
}

export interface BlockItem {
  id: number;
  blocked: PublicUser;
  created_at: string;
}

export interface DmMediaItem {
  id: number;
  thread_id: number;
  url: string | null;
  name: string;
  attachment_type: "image" | "file" | "";
  from_me: boolean;
  sender: string;
  other: string;
  created_at: string;
}

export interface SearchResults {
  users: PublicUser[];
  games: GameListItem[];
  posts: Post[];
}

export const searchApi = {
  search(q: string, type: "all" | "users" | "games" | "posts" = "all") {
    const params = new URLSearchParams({ q, type });
    return api<SearchResults>(`/api/search?${params.toString()}`);
  },
};

export const meApi = {
  update(patch: Partial<Pick<Me, "display_name" | "bio" | "is_private" | "notify_follows" | "notify_likes" | "notify_comments">>) {
    return api<Me>("/api/me", { method: "PATCH", body: JSON.stringify(patch) });
  },
  updateAvatar(avatar: File) {
    const fd = new FormData();
    fd.append("avatar", avatar);
    return api<Me>("/api/me", { method: "PATCH", body: fd });
  },
  activity() {
    return api<ActivitySummary>("/api/me/activity");
  },
  notifications() {
    return api<Notification[]>("/api/me/notifications");
  },
  comments() {
    return api<MyComment[]>("/api/me/comments");
  },
  favorites() {
    return api<{ games: GameListItem[]; posts: Post[] }>("/api/me/favorites");
  },
};

export const friendsApi = {
  followers(username: string) {
    return api<PublicUser[]>(`/api/users/${username}/followers`);
  },
  following(username: string) {
    return api<PublicUser[]>(`/api/users/${username}/following`);
  },
  requests() {
    return api<FollowRequestItem[]>("/api/follow-requests");
  },
  resolve(id: number, action: "accept" | "reject") {
    return api<{ status: string }>(`/api/follow-requests/${id}/${action}`, { method: "POST" });
  },
};

export type ReportKind = "user" | "game" | "post" | "comment" | "other";
export type ReportReason = "spam" | "abuse" | "hate" | "sexual" | "illegal" | "other";

export const safetyApi = {
  blocks() {
    return api<BlockItem[]>("/api/blocks");
  },
  block(username: string) {
    return api<{ blocked: boolean }>(`/api/blocks/${username}`, { method: "POST" });
  },
  unblock(username: string) {
    return api(`/api/blocks/${username}`, { method: "DELETE" });
  },
  report(body: { kind: ReportKind; target: string; reason: ReportReason; note?: string }) {
    return api("/api/reports", { method: "POST", body: JSON.stringify(body) });
  },
};

export const dmApi = {
  media() {
    return api<DmMediaItem[]>("/api/dm/media");
  },
  sendAttachment(threadId: number, file: File, body = "") {
    const fd = new FormData();
    fd.append("file", file);
    if (body) fd.append("body", body);
    return api<ChatMessage>(`/api/dm/threads/${threadId}/attachments`, { method: "POST", body: fd });
  },
};

// ---- games ------------------------------------------------------------------

export const API_BASE_URL = API_BASE;

export type Engine = "html" | "unity_webgl";
export type Kind = "normal" | "story";
export type Visibility = "public" | "followers" | "private";
export type Genre =
  | "action" | "adventure" | "rpg" | "shooter" | "platformer" | "puzzle"
  | "arcade" | "strategy" | "simulation" | "sports" | "racing" | "horror"
  | "casual" | "other";

// Display order + labels for genre sections and the upload picker.
export const GENRES: { value: Genre; label: string }[] = [
  { value: "action", label: "Action" },
  { value: "adventure", label: "Adventure" },
  { value: "rpg", label: "RPG" },
  { value: "shooter", label: "Shooter" },
  { value: "platformer", label: "Platformer" },
  { value: "puzzle", label: "Puzzle" },
  { value: "arcade", label: "Arcade" },
  { value: "strategy", label: "Strategy" },
  { value: "simulation", label: "Simulation" },
  { value: "sports", label: "Sports" },
  { value: "racing", label: "Racing" },
  { value: "horror", label: "Horror" },
  { value: "casual", label: "Casual" },
  { value: "other", label: "Other" },
];

export const GENRE_LABELS: Record<Genre, string> = Object.fromEntries(
  GENRES.map((g) => [g.value, g.label]),
) as Record<Genre, string>;

export interface GameListItem {
  id: number;
  slug: string;
  title: string;
  engine: Engine;
  kind: Kind;
  genre: Genre;
  visibility: Visibility;
  status: "draft" | "deployed";
  thumbnail: string | null;
  is_paid: boolean;
  price: string;
  currency: string;
  play_count: number;
  likes_count: number;
  owner: PublicUser;
  created_at: string;
}

export interface GameDetail extends GameListItem {
  description: string;
  entry_file: string;
  play_url: string;
  is_liked_by_me: boolean;
  is_saved_by_me: boolean;
  scenes: { order: number; title: string; entry_file: string }[];
  deployed_at: string | null;
}

export interface Comment {
  id: number;
  user: PublicUser;
  body: string;
  created_at: string;
}

export interface CreateGameMeta {
  title: string;
  description?: string;
  engine: Engine;
  kind?: Kind;
  genre?: Genre;
  visibility?: Visibility;
  is_paid?: boolean;
  price?: number;
  currency?: string;
}

function metaForm(meta: CreateGameMeta, thumbnail?: File | null): FormData {
  const fd = new FormData();
  Object.entries(meta).forEach(([k, v]) => {
    if (v !== undefined && v !== null) fd.append(k, String(v));
  });
  if (thumbnail) fd.append("thumbnail", thumbnail);
  return fd;
}

export const gamesApi = {
  list(params: { owner?: string; mine?: boolean; genre?: Genre } = {}) {
    const q = new URLSearchParams();
    if (params.owner) q.set("owner", params.owner);
    if (params.mine) q.set("mine", "1");
    if (params.genre) q.set("genre", params.genre);
    const qs = q.toString();
    return api<GameListItem[]>(`/api/games${qs ? `?${qs}` : ""}`);
  },
  get(slug: string) {
    return api<GameDetail>(`/api/games/${slug}`);
  },
  create(meta: CreateGameMeta, bundle: Blob, thumbnail?: File | null) {
    const fd = metaForm(meta, thumbnail);
    fd.append("bundle", bundle, "bundle.zip");
    return api<GameDetail>("/api/games", { method: "POST", body: fd });
  },
  // Upload the game's files/folders directly (no zipping). Each entry carries its
  // relative path so folder structure (e.g. Unity WebGL Build/) is preserved.
  createFromFiles(meta: CreateGameMeta, entries: { path: string; file: File }[], thumbnail?: File | null) {
    const fd = metaForm(meta, thumbnail);
    for (const { path, file } of entries) {
      fd.append("files", file, file.name);
      fd.append("paths", path);
    }
    return api<GameDetail>("/api/games", { method: "POST", body: fd });
  },
  play(slug: string) {
    return api<{ play_url: string }>(`/api/games/${slug}/play`, { method: "POST" });
  },
  like(slug: string, on: boolean) {
    return api<{ liked: boolean; likes_count: number }>(
      `/api/games/${slug}/like`,
      { method: on ? "POST" : "DELETE" },
    );
  },
  save(slug: string, on: boolean) {
    return api<{ saved: boolean }>(`/api/games/${slug}/save`, {
      method: on ? "POST" : "DELETE",
    });
  },
  comments(slug: string) {
    return api<Comment[]>(`/api/games/${slug}/comments`);
  },
  addComment(slug: string, body: string) {
    return api<Comment>(`/api/games/${slug}/comments`, {
      method: "POST",
      body: JSON.stringify({ body }),
    });
  },
  saved() {
    return api<{ id: number; game: GameListItem; created_at: string }[]>("/api/me/saved");
  },
};

// Resolve a possibly-relative media URL (e.g. "media/…" or "/media/…") to an
// absolute one, normalising the slash between host and path.
export function mediaUrl(path: string | null): string | null {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  const base = API_BASE.replace(/\/$/, "");
  const rel = path.startsWith("/") ? path : `/${path}`;
  return `${base}${rel}`;
}

// ---- IDE --------------------------------------------------------------------

export interface LanguageMark {
  ext: string;
  label: string;
  color: string;
}

export interface ProjectFile {
  id: number;
  path: string;
  content: string;
  order: number;
  language: LanguageMark;
  updated_at: string;
}

export interface ProjectSummary {
  id: number;
  slug: string;
  name: string;
  kind: "normal" | "story" | "code";
  deployed_slug: string | null;
  updated_at: string;
  created_at: string;
}

export interface ProjectDetail extends ProjectSummary {
  files: ProjectFile[];
}

export interface RunResult {
  // "preview" => run live in the webview; "terminal" => server terminal output.
  mode?: "preview" | "terminal";
  entry?: string;
  command: string;
  stdout: string;
  stderr: string;
  exit_code: number;
  timed_out: boolean;
}

export const ideApi = {
  templates() {
    return api<{ id: string; label: string; kind: string }[]>("/api/ide/templates");
  },
  projects() {
    return api<ProjectSummary[]>("/api/ide/projects");
  },
  create(name: string, template: string) {
    return api<ProjectDetail>("/api/ide/projects", {
      method: "POST",
      body: JSON.stringify({ name, template }),
    });
  },
  get(slug: string) {
    return api<ProjectDetail>(`/api/ide/projects/${slug}`);
  },
  remove(slug: string) {
    return api(`/api/ide/projects/${slug}`, { method: "DELETE" });
  },
  addFile(slug: string, path: string, content = "") {
    return api<ProjectFile>(`/api/ide/projects/${slug}/files`, {
      method: "POST",
      body: JSON.stringify({ path, content }),
    });
  },
  saveFile(fileId: number, content: string) {
    return api<ProjectFile>(`/api/ide/files/${fileId}`, {
      method: "PATCH",
      body: JSON.stringify({ content }),
    });
  },
  deleteFile(fileId: number) {
    return api(`/api/ide/files/${fileId}`, { method: "DELETE" });
  },
  run(slug: string) {
    return api<RunResult>(`/api/ide/projects/${slug}/run`, { method: "POST" });
  },
  deploy(slug: string) {
    return api<GameDetail>(`/api/ide/projects/${slug}/deploy`, { method: "POST" });
  },
};

// ---- payments ---------------------------------------------------------------

export interface Purchase {
  id: number;
  game_slug: string;
  game_title: string;
  amount: string;
  currency: string;
  commission_rate: string;
  platform_fee: string;
  seller_amount: string;
  status: string;
  simulated: boolean;
}

export const paymentsApi = {
  checkout(slug: string) {
    return api<Purchase>(`/api/payments/checkout/${slug}`, { method: "POST" });
  },
  confirm(id: number) {
    return api<Purchase>(`/api/payments/confirm/${id}`, { method: "POST" });
  },
  onboarding() {
    return api<{ mode: string; url: string }>("/api/payments/onboarding", { method: "POST" });
  },
};

// ---- community --------------------------------------------------------------

export type PostVisibility = "public" | "followers" | "private";

export interface PostMedia {
  id: number;
  media_type: "image" | "video";
  url: string; // signed, relative to API base
  order: number;
}

export interface Post {
  id: number;
  author: PublicUser;
  body: string;
  visibility: PostVisibility;
  media: PostMedia[];
  likes_count: number;
  comments_count: number;
  is_liked_by_me: boolean;
  created_at: string;
}

// ---- chat -------------------------------------------------------------------

export interface ChatMessage {
  id: number;
  sender: string;
  sender_id: number;
  body: string;
  created_at: string;
  // DM attachments (absent on room/text messages).
  attachment_url?: string | null;
  attachment_name?: string;
  attachment_type?: "image" | "file" | "";
}

export interface DirectThread {
  id: number;
  other: PublicUser;
  last_message: string;
  last_message_at: string | null;
  created_at: string;
}

export interface ChatRoom {
  id: number;
  slug: string;
  name: string;
  description: string;
}

export const chatApi = {
  threads() {
    return api<DirectThread[]>("/api/dm/threads");
  },
  startWith(username: string) {
    return api<DirectThread>(`/api/dm/with/${username}`, { method: "POST" });
  },
  threadMessages(id: number) {
    return api<ChatMessage[]>(`/api/dm/threads/${id}/messages`);
  },
  rooms() {
    return api<ChatRoom[]>("/api/rooms");
  },
  roomMessages(slug: string) {
    return api<ChatMessage[]>(`/api/rooms/${slug}/messages`);
  },
};

// Build a WebSocket URL against the API host, carrying the access token.
// Same-origin deploys have an empty API_BASE → derive from the current page.
export function wsUrl(path: string): string {
  let base = API_BASE;
  if (!base && typeof window !== "undefined") base = window.location.origin;
  const httpBase = base.replace(/\/$/, "");
  const wsBase = httpBase.replace(/^http/, "ws");
  const token = tokens.access ?? "";
  const sep = path.includes("?") ? "&" : "?";
  return `${wsBase}${path}${sep}token=${encodeURIComponent(token)}`;
}

// ---- shorts -----------------------------------------------------------------

export interface Short {
  id: number;
  author: PublicUser;
  caption: string;
  visibility: PostVisibility;
  video_url: string;
  view_count: number;
  likes_count: number;
  is_liked_by_me: boolean;
  created_at: string;
}

export const shortsApi = {
  list(params: { mine?: boolean } = {}) {
    const qs = params.mine ? "?mine=1" : "";
    return api<Short[]>(`/api/shorts${qs}`);
  },
  create(caption: string, visibility: PostVisibility, video: File) {
    const fd = new FormData();
    fd.append("caption", caption);
    fd.append("visibility", visibility);
    fd.append("video", video);
    return api<Short>("/api/shorts", { method: "POST", body: fd });
  },
  like(id: number, on: boolean) {
    return api<{ liked: boolean; likes_count: number }>(`/api/shorts/${id}/like`, {
      method: on ? "POST" : "DELETE",
    });
  },
};

export const postsApi = {
  list(params: { user?: string; feed?: "explore" } = {}) {
    const q = new URLSearchParams();
    if (params.user) q.set("user", params.user);
    if (params.feed) q.set("feed", params.feed);
    const qs = q.toString();
    return api<Post[]>(`/api/posts${qs ? `?${qs}` : ""}`);
  },
  get(id: number) {
    return api<Post>(`/api/posts/${id}`);
  },
  create(body: string, visibility: PostVisibility, media: File[]) {
    const fd = new FormData();
    fd.append("body", body);
    fd.append("visibility", visibility);
    media.forEach((f) => fd.append("media", f));
    return api<Post>("/api/posts", { method: "POST", body: fd });
  },
  like(id: number, on: boolean) {
    return api<{ liked: boolean; likes_count: number }>(`/api/posts/${id}/like`, {
      method: on ? "POST" : "DELETE",
    });
  },
  remove(id: number) {
    return api(`/api/posts/${id}`, { method: "DELETE" });
  },
  comments(id: number) {
    return api<Comment[]>(`/api/posts/${id}/comments`);
  },
  addComment(id: number, body: string) {
    return api<Comment>(`/api/posts/${id}/comments`, {
      method: "POST",
      body: JSON.stringify({ body }),
    });
  },
};
