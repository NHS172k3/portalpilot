import { MirrorForm } from "./mirror-form";

type PageProps = {
  params: Promise<{ formId: string }>;
  searchParams: Promise<{ replay?: string; taskId?: string }>;
};

export default async function MirrorPage({ params, searchParams }: PageProps) {
  const { formId } = await params;
  const { replay, taskId } = await searchParams;
  return <MirrorForm formId={formId} replay={replay === "1"} taskId={taskId} />;
}
