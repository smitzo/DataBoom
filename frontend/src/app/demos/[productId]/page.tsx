import { notFound } from "next/navigation";

import { DemoWorkspaceDashboard } from "@/components/demo-workspace";
import { PublicShell } from "@/components/layout";
import { demoWorkspaces, getDemoWorkspace } from "@/data/demo-workspaces";

export function generateStaticParams() {
  return demoWorkspaces.map((workspace) => ({ productId: workspace.id }));
}

export default async function DemoWorkspacePage({
  params,
}: {
  params: Promise<{ productId: string }>;
}) {
  const { productId } = await params;
  const workspace = getDemoWorkspace(productId);

  if (!workspace) {
    notFound();
  }

  return (
    <PublicShell>
      <DemoWorkspaceDashboard workspace={workspace} />
    </PublicShell>
  );
}
