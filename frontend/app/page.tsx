import { LiveScoreboard } from "@/components/LiveScoreboard";

export default function Home() {
  return (
    <main className="min-h-screen bg-black p-8">
      <h1 className="text-xl font-semibold mb-4">Live Matches</h1>
      <LiveScoreboard />
    </main>
  );
}