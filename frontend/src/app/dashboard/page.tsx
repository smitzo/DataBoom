"use client";

import { AuthGate } from "@/components/auth-gate";
import { DataWorkspace } from "@/components/data-workspace";

export default function DashboardPage() {
  return (
    <AuthGate>
      {(session) => <DataWorkspace session={session} />}
    </AuthGate>
  );
}
