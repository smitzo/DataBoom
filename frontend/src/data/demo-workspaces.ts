import type { ProductCatalogItem } from "@/data/workbench";
import { productCatalog } from "@/data/workbench";

export type DemoWorkspaceKind = "relational" | "document" | "planned";

export type DemoTableRow = Record<string, string>;

export type DemoWorkspaceResource = {
  name: string;
  count: number;
};

export type DemoWorkspace = {
  id: string;
  name: string;
  kind: DemoWorkspaceKind;
  module: string;
  engine: string;
  database: string;
  schema: string;
  host: string;
  rows: number;
  columns: number;
  artifacts: number;
  lastSync: string;
  resources: DemoWorkspaceResource[];
  tableColumns: string[];
  tableRows: DemoTableRow[];
  documents: Record<string, unknown>[];
  statusCounts: { label: string; count: number; tone: string }[];
  description: string;
};

const tableRows = Array.from({ length: 10 }, (_, index) => {
  const rowNumber = index + 1;
  const statusCycle = ["failed", "failed", "pending", "failed", "pending", "pending", "pending", "failed", "posted", "reversed"];
  return {
    id: String(rowNumber),
    full_name: `Full Name ${rowNumber}`,
    email: `user${rowNumber}-${String(57173 + rowNumber * 1739).slice(0, 5)}@example.test`,
    phone: `+1555${String(2100000 + rowNumber * 41789).slice(0, 7)}`,
    segment: `public_customers_segment_${rowNumber}_${String(34029 + rowNumber * 8543).slice(0, 5)}`,
    status: statusCycle[index] ?? "pending",
  };
});

const documentSamples = [
  {
    _id: "00000000c184ae47c3e64cbf",
    email: "customer1@example.test",
    status: "active",
    profile: {
      first_name: "Samir",
      last_name: "Morgan",
      age: 31,
      loyalty_tier: "standard",
    },
    addresses: [{ city: "Chicago", country: "US", postal_code: "53677" }],
  },
  {
    _id: "00000007e2b999f4d5de4aa",
    email: "customer2@example.test",
    status: "blocked",
    profile: {
      first_name: "Avery",
      last_name: "Rivera",
      age: 61,
      loyalty_tier: "platinum",
    },
    addresses: [{ city: "Boston", country: "US", postal_code: "90537" }],
  },
];

export const demoWorkspaces: DemoWorkspace[] = [
  {
    id: "table-boom",
    name: "Table-Boom",
    kind: "relational",
    module: "Relational data",
    engine: "PostgreSQL",
    database: "table_boom_local_demo",
    schema: "public",
    host: "postgresql-cmp-proxy:5432",
    rows: 232,
    columns: 20,
    artifacts: 17,
    lastSync: "2m ago",
    resources: [
      { name: "customers", count: 24 },
      { name: "products", count: 16 },
      { name: "orders", count: 48 },
      { name: "order_items", count: 96 },
      { name: "payments", count: 48 },
      { name: "analytics_events", count: 12 },
    ],
    tableColumns: ["id", "full_name", "email", "phone", "segment", "status"],
    tableRows,
    documents: [],
    statusCounts: [
      { label: "Failed", count: 5, tone: "bg-red-400" },
      { label: "Pending", count: 5, tone: "bg-amber-300" },
      { label: "Posted", count: 1, tone: "bg-cyan-300" },
      { label: "Reversed", count: 5, tone: "bg-fuchsia-400" },
      { label: "Other", count: 216, tone: "bg-slate-500" },
    ],
    description:
      "Relational workspace for tables, primary keys, foreign keys, CSV, SQL, previews, and run validation.",
  },
  {
    id: "docu-boom",
    name: "Docu-Boom",
    kind: "document",
    module: "NoSQL document data",
    engine: "MongoDB-style document engine",
    database: "docu_boom_local_demo",
    schema: "collections",
    host: "local document workspace",
    rows: 340,
    columns: 18,
    artifacts: 8,
    lastSync: "1m ago",
    resources: [
      { name: "customers", count: 40 },
      { name: "orders", count: 120 },
      { name: "events", count: 180 },
    ],
    tableColumns: [],
    tableRows: [],
    documents: documentSamples,
    statusCounts: [
      { label: "Active", count: 214, tone: "bg-cyan-300" },
      { label: "Blocked", count: 42, tone: "bg-red-400" },
      { label: "Pending", count: 84, tone: "bg-amber-300" },
    ],
    description:
      "Document workspace for nested JSON, NDJSON, stable object identifiers, arrays, and collection-level artifacts.",
  },
  plannedWorkspace("graph-boom"),
  plannedWorkspace("masker-boom"),
];

export function getDemoWorkspace(productId: string) {
  return demoWorkspaces.find((workspace) => workspace.id === productId) ?? null;
}

export function productCatalogItem(productId: string): ProductCatalogItem | null {
  return productCatalog.find((product) => slugProductName(product.name) === productId) ?? null;
}

function plannedWorkspace(productId: string): DemoWorkspace {
  const catalogItem = productCatalogItem(productId);
  return {
    id: productId,
    name: catalogItem?.name ?? productId,
    kind: "planned",
    module: catalogItem?.module ?? "Planned workspace",
    engine: "Roadmap engine",
    database: `${productId}_preview`,
    schema: "planned",
    host: "roadmap",
    rows: 0,
    columns: 0,
    artifacts: 0,
    lastSync: "planned",
    resources: [],
    tableColumns: [],
    tableRows: [],
    documents: [],
    statusCounts: [],
    description: catalogItem?.summary ?? "Planned workspace preview.",
  };
}

function slugProductName(name: string) {
  return name.toLowerCase();
}
