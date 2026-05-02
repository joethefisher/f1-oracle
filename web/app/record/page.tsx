import { getSeasonRecords } from "@/lib/queries";
import RecordView from "./RecordView";

export const revalidate = 300;

export default async function RecordPage() {
  const records = await getSeasonRecords();
  return <RecordView records={records} />;
}
