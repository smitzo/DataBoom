"use client";

import { AuthGate } from "@/components/auth-gate";
import { RelationalWorkspace } from "@/components/relational-workspace";

export default function DashboardPage() {
  return (
    <AuthGate>
      {(session) => <RelationalWorkspace session={session} />}
    </AuthGate>
  );
}
