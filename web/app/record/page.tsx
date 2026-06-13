import type { Metadata } from "next";
import { getSeasonRecords, getActiveRace, getSeasonTotalRaces } from "@/lib/queries";
import RecordView from "./RecordView";

export const revalidate = 300;

export const metadata: Metadata = {
  title: "Record — F1 Oracle",
  description:
    "F1 Oracle's season-long prediction record against Kalshi markets. Hit rate, ROI, calibration, and graded prediction history.",
  alternates: { canonical: "/record" },
  openGraph: {
    title: "Record — F1 Oracle",
    description:
      "Season-long prediction record + calibration vs Kalshi F1 markets.",
    url: "/record",
    type: "website",
  },
};

export default async function RecordPage() {
  const [records, activeRace] = await Promise.all([
    getSeasonRecords(),
    getActiveRace(),
  ]);
  const season = records[0]?.race.season ?? activeRace?.season ?? new Date().getFullYear();
  const totalRaces = await getSeasonTotalRaces(season);
  return <RecordView records={records} season={season} activeRace={activeRace} totalRaces={totalRaces} />;
}
