"use client";

import { use, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  gamesApi,
  paymentsApi,
  mediaUrl,
  ApiError,
  GameDetail,
  Comment,
  GENRE_LABELS,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { BookmarkIcon, HeartIcon, MaximizeIcon, PlayIcon } from "@/components/icons";

export default function GamePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);
  const { user } = useAuth();
  const [game, setGame] = useState<GameDetail | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "denied" | "notfound">("loading");
  const [playing, setPlaying] = useState(false);
  const [sceneIndex, setSceneIndex] = useState(0);
  const [comments, setComments] = useState<Comment[]>([]);
  const [draft, setDraft] = useState("");
  const [buying, setBuying] = useState(false);
  const [purchaseMsg, setPurchaseMsg] = useState<string | null>(null);
  const playerRef = useRef<HTMLDivElement>(null);

  function goFullscreen() {
    const el = playerRef.current;
    if (!el) return;
    if (document.fullscreenElement) document.exitFullscreen();
    else el.requestFullscreen?.();
  }

  // Story games: a scene posts `gameplatform:next-scene` when it completes; we
  // advance to the next scene automatically.
  useEffect(() => {
    function onMessage(e: MessageEvent) {
      if (e.data?.type === "gameplatform:next-scene") {
        setSceneIndex((i) => i + 1);
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  async function buy() {
    if (!game) return;
    setBuying(true);
    setPurchaseMsg(null);
    try {
      const p = await paymentsApi.checkout(slug);
      // Simulation mode: confirm immediately (stands in for the Stripe webhook).
      if (p.simulated) await paymentsApi.confirm(p.id);
      setPurchaseMsg(
        `Purchased. Seller gets ${p.currency} ${p.seller_amount}, platform fee ${p.currency} ${p.platform_fee} (${Math.round(Number(p.commission_rate) * 100)}%).`,
      );
    } catch (err) {
      setPurchaseMsg(err instanceof ApiError ? `Purchase failed: ${JSON.stringify(err.data)}` : "Purchase failed");
    } finally {
      setBuying(false);
    }
  }

  useEffect(() => {
    (async () => {
      try {
        const g = await gamesApi.get(slug);
        setGame(g);
        setState("ready");
        setComments(await gamesApi.comments(slug));
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) setState("denied");
        else if (err instanceof ApiError && err.status === 404) setState("notfound");
        else setState("notfound");
      }
    })();
  }, [slug]);

  async function play() {
    if (!game) return;
    try {
      await gamesApi.play(slug);
      setPlaying(true);
      setGame({ ...game, play_count: game.play_count + 1 });
    } catch {
      /* ignore */
    }
  }

  async function toggleLike() {
    if (!game) return;
    const r = await gamesApi.like(slug, !game.is_liked_by_me);
    setGame({ ...game, is_liked_by_me: r.liked, likes_count: r.likes_count });
  }

  async function toggleSave() {
    if (!game) return;
    const r = await gamesApi.save(slug, !game.is_saved_by_me);
    setGame({ ...game, is_saved_by_me: r.saved });
  }

  async function submitComment(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.trim()) return;
    const c = await gamesApi.addComment(slug, draft.trim());
    setComments([c, ...comments]);
    setDraft("");
  }

  if (state === "loading") return <p className="text-neutral-500">Loading…</p>;
  if (state === "denied")
    return <p className="text-neutral-500">This game is private or followers-only.</p>;
  if (state === "notfound" || !game)
    return <p className="text-neutral-500">Game not found.</p>;

  // For story games the current scene URL is derived from the scene list;
  // otherwise use the single entry play URL. Scene files sit under the same
  // signed-cookie path, so the play authorisation covers them all.
  const isStory = game.kind === "story" && game.scenes.length > 0;
  const storyDone = isStory && sceneIndex >= game.scenes.length;
  const currentSrc = isStory
    ? mediaUrl(`/media/games/${game.id}/${game.scenes[Math.min(sceneIndex, game.scenes.length - 1)].entry_file}`)
    : mediaUrl(game.play_url);

  return (
    <div className="space-y-5">
      {/* Player */}
      <div className="overflow-hidden rounded-2xl border border-neutral-800 bg-black">
        <div ref={playerRef} className="relative aspect-video w-full bg-black">
          {playing && storyDone ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-white">
              <span className="text-lg font-medium">The end</span>
              <button
                onClick={() => setSceneIndex(0)}
                className="rounded-lg border border-neutral-600 px-4 py-2 text-sm hover:bg-neutral-800"
              >
                Replay from start
              </button>
            </div>
          ) : playing && currentSrc ? (
            <iframe
              key={isStory ? sceneIndex : "single"}
              src={currentSrc}
              title={game.title}
              className="h-full w-full"
              // Unity WebGL needs same-origin for IndexedDB; content is served
              // from the API origin, isolated from this app.
              sandbox="allow-scripts allow-same-origin allow-pointer-lock allow-fullscreen"
              allow="fullscreen; autoplay; gamepad; cross-origin-isolated"
            />
          ) : (
            <button onClick={play} className="group absolute inset-0 flex items-center justify-center overflow-hidden">
              {/* Thumbnail poster (falls back to a gradient, not a black joystick). */}
              {mediaUrl(game.thumbnail) ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={mediaUrl(game.thumbnail) ?? undefined} alt={game.title} className="absolute inset-0 h-full w-full object-cover" />
              ) : (
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-600 via-purple-700 to-fuchsia-700" />
              )}
              <div className="absolute inset-0 bg-black/30 transition group-hover:bg-black/40" />
              <div className="relative flex flex-col items-center gap-2 text-white">
                <span className="flex h-16 w-16 items-center justify-center rounded-full bg-white/20 backdrop-blur transition group-hover:scale-110">
                  <PlayIcon filled className="h-8 w-8" />
                </span>
                <span className="font-medium">Play</span>
              </div>
            </button>
          )}

          {/* Fullscreen — works for Unity WebGL and HTML games alike. */}
          {playing && (
            <button
              onClick={goFullscreen}
              title="전체화면"
              className="absolute right-2 top-2 z-10 rounded-lg bg-black/55 p-2 text-white backdrop-blur hover:bg-black/75"
            >
              <MaximizeIcon className="h-4 w-4" />
            </button>
          )}
        </div>
        {playing && isStory && !storyDone && (
          <div className="flex items-center justify-between border-t border-neutral-800 px-4 py-2 text-xs text-neutral-400">
            <span>Scene {sceneIndex + 1} / {game.scenes.length}</span>
            <button
              onClick={() => setSceneIndex((i) => i + 1)}
              className="rounded-md border border-neutral-700 px-3 py-1 hover:bg-neutral-800"
            >
              Next scene
            </button>
          </div>
        )}
      </div>

      {/* Meta */}
      <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold">{game.title}</h1>
            <Link href={`/u/${game.owner.username}`} className="text-sm text-indigo-500">
              @{game.owner.username}
            </Link>
            <div className="mt-1 flex items-center gap-3 text-xs text-neutral-400">
              <span className="inline-flex items-center gap-1"><PlayIcon className="h-3.5 w-3.5" /> {game.play_count} plays</span>
              <span className="rounded-full bg-neutral-800 px-2 py-0.5">{GENRE_LABELS[game.genre]}</span>
              <span>{game.engine === "unity_webgl" ? "Unity WebGL" : "HTML"}</span>
              {game.is_paid ? (
                <span className="text-amber-500">{game.currency} {Number(game.price).toFixed(2)}</span>
              ) : (
                <span className="text-emerald-500">Free</span>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={toggleLike}
              className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm ${
                game.is_liked_by_me
                  ? "border-rose-400/40 bg-rose-950/40 text-rose-400"
                  : "border-neutral-700"
              }`}
            >
              <HeartIcon filled={game.is_liked_by_me} className="h-4 w-4" /> {game.likes_count}
            </button>
            <button
              onClick={toggleSave}
              className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm ${
                game.is_saved_by_me
                  ? "border-indigo-400/40 bg-indigo-950/40 text-indigo-400"
                  : "border-neutral-700"
              }`}
            >
              <BookmarkIcon filled={game.is_saved_by_me} className="h-4 w-4" />
              {game.is_saved_by_me ? "Saved" : "Save"}
            </button>
          </div>
        </div>
        {game.description && (
          <p className="mt-3 whitespace-pre-wrap text-sm text-neutral-300">
            {game.description}
          </p>
        )}

        {game.is_paid && user && user.username !== game.owner.username && (
          <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-950/20 p-3">
            <button
              onClick={buy}
              disabled={buying}
              className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-black hover:bg-amber-400 disabled:opacity-50"
            >
              {buying ? "Processing…" : `Buy for ${game.currency} ${Number(game.price).toFixed(2)}`}
            </button>
            <p className="mt-2 text-xs text-neutral-400">
              The platform routes payment buyer→seller and keeps a 20% fee. No card
              data is stored here — handled by the payment provider.
            </p>
            {purchaseMsg && <p className="mt-2 text-xs text-emerald-400">{purchaseMsg}</p>}
          </div>
        )}
      </div>

      {/* Comments */}
      <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-5">
        <h2 className="font-semibold">Comments</h2>
        {user && (
          <form onSubmit={submitComment} className="mt-3 flex gap-2">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Add a comment…"
              className="flex-1 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 text-sm outline-none focus:border-indigo-500"
            />
            <button className="rounded-lg bg-indigo-500 px-4 text-sm font-medium text-white">Post</button>
          </form>
        )}
        <ul className="mt-4 space-y-3">
          {comments.map((c) => (
            <li key={c.id} className="text-sm">
              <Link href={`/u/${c.user.username}`} className="font-medium text-indigo-500">
                @{c.user.username}
              </Link>{" "}
              <span className="text-neutral-700 dark:text-neutral-300">{c.body}</span>
            </li>
          ))}
          {comments.length === 0 && (
            <li className="text-sm text-neutral-400">No comments yet.</li>
          )}
        </ul>
      </div>
    </div>
  );
}
