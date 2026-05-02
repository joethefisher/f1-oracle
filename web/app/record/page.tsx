import { getSeasonRecords } from "@/lib/queries";
import RecordView from "./RecordView";

export const revalidate = 300;

export default async function RecordPage() {
  const records = await getSeasonRecords();
  const season = records[0]?.race.season;
  return <RecordView records={records} season={season} />;
}
