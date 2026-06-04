"use client";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="space-y-3">
      <h2 className="text-lg font-bold text-red-400">Something went wrong</h2>
      <p className="text-sm text-zinc-400">{error.message}</p>
      <button onClick={reset} className="text-sm text-accent hover:underline">
        Try again
      </button>
    </div>
  );
}
