import { getActiveRace, getRacePredictions } from "@/lib/queries";
import RaceView from "./RaceView";

export const revalidate = 300; // re-fetch every 5 minutes

export default async function RacePage() {
  const race = await getActiveRace();

  if (!race) {
    return (
      <div className="rounded-lg border border-zinc-800 p-8 text-center text-zinc-500 text-sm">
        No active race weekend. Check back on race week.
      </div>
    );
  }

  const predictions = await getRacePredictions(race.id);

  return <RaceView race={race} predictions={predictions} />;
}
