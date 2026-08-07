import {
  Activity,
  CheckCircle2,
  Cpu,
  Database,
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  GitBranch,
  Server,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type IconConfig = LucideIcon;

export type ProfileConfig = {
  name: string;
  role: string;
  description: string;
  tags: string[];
  icon: IconConfig;
  selected: boolean;
  tone: string;
};

export type PipelineStepConfig = {
  label: string;
  detail: string;
  icon: IconConfig;
};

export type FormatConfig = {
  name: string;
  icon: IconConfig;
  state: string;
};

export type ValidationMetricConfig = {
  label: string;
  value: string;
  icon: IconConfig;
  success?: boolean;
};

export type DemoDatasetConfig = {
  name: string;
  tables: string;
  rows: string;
  tone: string;
};

export type RoadmapStatus = "achieved" | "next" | "planned";

export type RoadmapItem = {
  phase: string;
  status: RoadmapStatus;
  title: string;
  description: string;
  achieved: string[];
  future: string[];
};

export const navItems = [
  { label: "Products", href: "/products" },
  { label: "Demos", href: "/demos" },
  { label: "Roadmap", href: "/roadmap" },
  { label: "Contact", href: "/contact" },
];

export const heroMetrics = [
  { label: "Benchmark", value: "100k rows", tone: "text-emerald-300" },
  { label: "Memory", value: "50.7 MB", tone: "text-sky-300" },
  { label: "Exports", value: "CSV JSON SQL", tone: "text-amber-200" },
];

export const profiles: ProfileConfig[] = [
  {
    name: "Table-Boom",
    role: "Relational table data",
    description: "Key-safe relational datasets with CSV, JSON, and SQL exports.",
    tags: ["tables", "foreign keys"],
    icon: Database,
    selected: true,
    tone: "border-emerald-300/40 text-emerald-200",
  },
  {
    name: "Docu-Boom",
    role: "NoSQL document data",
    description: "MongoDB-style nested JSON and NDJSON collections with document previews.",
    tags: ["json", "ndjson"],
    icon: FileJson,
    selected: false,
    tone: "border-rose-300/40 text-rose-200",
  },
  {
    name: "Graph-Boom",
    role: "Planned graph data",
    description: "Node and edge datasets with labels, properties, and graph validation.",
    tags: ["nodes", "edges"],
    icon: GitBranch,
    selected: false,
    tone: "border-sky-300/40 text-sky-200",
  },
  {
    name: "Masker-Boom",
    role: "Planned masking layer",
    description: "Redaction, tokenization, and integrity-preserving masking for sensitive data.",
    tags: ["masking", "privacy"],
    icon: ShieldCheck,
    selected: false,
    tone: "border-amber-300/40 text-amber-200",
  },
];

export const pipeline: PipelineStepConfig[] = [
  { label: "Schema parsing", detail: "PostgreSQL DDL", icon: Database },
  { label: "Relationship graph", detail: "FK-aware ordering", icon: GitBranch },
  { label: "Domain values", detail: "Profile overlays", icon: Sparkles },
  { label: "Streaming export", detail: "Local artifacts", icon: Download },
  { label: "Validation", detail: "Keys and manifest", icon: ShieldCheck },
  { label: "Benchmarking", detail: "100k baseline", icon: Activity },
];

export const formats: FormatConfig[] = [
  { name: "CSV", icon: FileSpreadsheet, state: "ready" },
  { name: "JSON", icon: FileJson, state: "ready" },
  { name: "SQL", icon: FileText, state: "ready" },
];

export const validationMetrics: ValidationMetricConfig[] = [
  { label: "Records", value: "100k", icon: Database },
  { label: "Elapsed", value: "44.7s", icon: Cpu },
  { label: "Peak memory", value: "50.7 MB", icon: Server },
  { label: "Status", value: "Passed", icon: CheckCircle2, success: true },
];

export const demos: DemoDatasetConfig[] = [
  {
    name: "Financial relational demo",
    tables: "customers, bank_accounts, transactions",
    rows: "1,100 rows",
    tone: "border-emerald-300/30",
  },
  {
    name: "Healthcare relational demo",
    tables: "patients, encounters, vitals",
    rows: "1,300 rows",
    tone: "border-rose-300/30",
  },
];

export const roadmap: RoadmapItem[] = [
  {
    phase: "Phase 1",
    status: "achieved",
    title: "Table-Boom relational foundation",
    description:
      "Table-Boom can generate deterministic relational data from PostgreSQL schema files and write validated local artifacts.",
    achieved: [
      "PostgreSQL DDL ingestion and normalized schema models.",
      "Relationship-aware generation with primary-key and foreign-key preservation.",
      "CSV, JSON, and SQL artifact export to local disk.",
      "Financial and healthcare demo profiles plus checked-in CSV datasets.",
      "100k-record benchmark with validation report.",
      "Static Next.js workbench with a reusable component structure.",
    ],
    future: ["Keep Phase 1 benchmark and demo data updated when generation behavior changes."],
  },
  {
    phase: "Phase 2",
    status: "achieved",
    title: "Table-Boom scale, API, profiling, and Docu-Boom",
    description:
      "This phase expands Table-Boom scale and access patterns, then adds Docu-Boom document generation for NoSQL use cases.",
    achieved: [
      "FastAPI app scaffold with health and readiness endpoints.",
      "Synchronous API generation runs with SQL-backed metadata in Dockerized runs.",
      "Dashboard flow for demo login, product subscriptions, product generation, table previews, and downloads.",
      "DataBoom workspace with product navigation, spreadsheet previews, document previews, agent steps, and exports.",
      "Demo login, product subscription, product-run generation, run detail, and table preview dashboard pages.",
      "Docu-Boom JSON and NDJSON generation with document previews.",
      "Artifact listing and download endpoints for completed local runs.",
      "Optional API-key protection for run and artifact routes.",
      "CLI plan preview and artifact re-validation commands.",
      "Live PostgreSQL schema introspection foundation.",
    ],
    future: [
      "Harden generation toward 500k records with chunk-aware validation.",
      "Expand FastAPI run status, validation detail, and long-running job controls.",
      "Add live PostgreSQL profiling and metadata introspection.",
      "Add custom schema upload, custom domain mapping, and saved generation templates.",
    ],
  },
  {
    phase: "Phase 3",
    status: "planned",
    title: "LLM-assisted planning, Graph-Boom, and operator UX",
    description:
      "Planning becomes more intelligent while DataBoom gains Graph-Boom support for connected datasets.",
    achieved: [],
    future: [
      "Add prompt packs, prompt cache keys, and validated planner output schemas.",
      "Add dry-run plan review before generation.",
      "Add Graph-Boom generation for nodes, edges, properties, and graph exports.",
      "Build operator-facing run review, plan review, and graph preview screens.",
    ],
  },
  {
    phase: "Phase 4",
    status: "planned",
    title: "Masker-Boom privacy and security hardening",
    description:
      "Sensitive-domain workflows become safer through Masker-Boom policy controls, redaction, tokenization, and privacy validation.",
    achieved: [],
    future: [
      "Add Masker-Boom policy files for synthetic replacement, hashing, tokenization, and redaction.",
      "Prevent raw sampled values from appearing in logs or reports.",
      "Add audit logs and privacy validation reports.",
    ],
  },
  {
    phase: "Phase 5",
    status: "planned",
    title: "Production release and extensibility",
    description:
      "The product becomes deployment-ready with CI, observability, retention controls, and adapter boundaries.",
    achieved: [],
    future: [
      "Add production deployment guides and CI build verification.",
      "Add health/readiness endpoints, structured logs, and run IDs.",
      "Add adapter boundaries for more databases, object storage, and future export targets.",
    ],
  },
];
