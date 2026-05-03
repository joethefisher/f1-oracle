import { getSeasonRecords, getActiveRace, getSeasonTotalRaces } from "@/lib/queries";
import RecordView from "./RecordView";

export const revalidate = 300;

export default async function RecordPage() {
  const [records, activeRace] = await Promise.all([
    getSeasonRecords(),
    getActiveRace(),
  ]);
  const season = records[0]?.race.season ?? activeRace?.season ?? new Date().getFullYear();
  const totalRaces = await getSeasonTotalRaces(season);
  return <RecordView records={records} season={season} activeRace={activeRace} totalRaces={totalRaces} />;
}
