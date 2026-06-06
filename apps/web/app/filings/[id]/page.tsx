import { FilingDetailClient } from "@/components/filing-detail-client";

export default async function FilingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <FilingDetailClient id={id} />;
}
