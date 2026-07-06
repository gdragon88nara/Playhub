import Link from "next/link";
import { GameListItem, mediaUrl, GENRE_LABELS } from "@/lib/api";
import { HeartIcon, LockIcon, PlayIcon } from "@/components/icons";

// A deterministic gradient poster used when a game has no cover image — much
// nicer than a lone joystick on black.
const GRADIENTS = [
  "from-indigo-500 to-fuchsia-600",
  "from-sky-500 to-indigo-600",
  "from-emerald-500 to-teal-600",
  "from-amber-500 to-orange-600",
  "from-rose-500 to-pink-600",
  "from-violet-500 to-purple-700",
];

export function GameCard({ game }: { game: GameListItem }) {
  const thumb = mediaUrl(game.thumbnail);
  const gradient = GRADIENTS[game.id % GRADIENTS.length];
  return (
    <Link
      href={`/games/${game.slug}`}
      className="group block overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 transition hover:shadow-md"
    >
      <div className="relative flex aspect-video items-center justify-center overflow-hidden">
        {thumb ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={thumb} alt={game.title} className="h-full w-full object-cover" />
        ) : (
          <div className={`flex h-full w-full items-center justify-center bg-gradient-to-br ${gradient}`}>
            <span className="text-4xl font-black uppercase text-white/90">
              {game.title.slice(0, 1)}
            </span>
          </div>
        )}
        <span className="absolute left-2 top-2 rounded-full bg-black/55 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur">
          {GENRE_LABELS[game.genre]}
        </span>
      </div>
      <div className="p-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="truncate font-semibold">{game.title}</h3>
          {game.is_paid ? (
            <span className="shrink-0 rounded-full bg-amber-100 text-amber-700 px-2 py-0.5 text-xs font-medium">
              {game.currency} {Number(game.price).toFixed(2)}
            </span>
          ) : (
            <span className="shrink-0 rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5 text-xs font-medium">
              Free
            </span>
          )}
        </div>
        <p className="mt-0.5 text-xs text-neutral-500">@{game.owner.username}</p>
        <div className="mt-2 flex items-center gap-3 text-xs text-neutral-400">
          <span className="inline-flex items-center gap-1"><PlayIcon className="h-3.5 w-3.5" /> {game.play_count}</span>
          <span className="inline-flex items-center gap-1"><HeartIcon className="h-3.5 w-3.5" /> {game.likes_count}</span>
          {game.visibility !== "public" && (
            <span className="inline-flex items-center gap-1"><LockIcon className="h-3.5 w-3.5" /> {game.visibility}</span>
          )}
        </div>
      </div>
    </Link>
  );
}
