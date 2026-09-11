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

export type RoadmapStatus = "achieved" | "next" | "planned";

export type ProfileConfig = {
  name: string;
  role: string;
  description: string;
  tags: string[];
  icon: IconConfig;
  selected: boolean;
  tone: string;
};

export type ProductCatalogItem = {
  name: string;
  module: string;
  status: RoadmapStatus;
  summary: string;
  detail: string;
  outputs: string[];
  capabilities: string[];
  useCases: string[];
  icon: IconConfig;
  accent: string;
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

export type RoadmapItem = {
  id: string;
  phase: string;
  status: RoadmapStatus;
  title: string;
  description: string;
  sections: {
    title: string;
    items: string[];
    empty: string;
  }[];
};

export const navItems = [
  { label: "Platform", href: "/#platform" },
  { label: "Products", href: "/products" },
  { label: "Demos", href: "/demos" },
  { label: "Roadmap", href: "/roadmap" },
  { label: "About", href: "/about" },
  { label: "Contact", href: "/contact" },
];

export const heroMetrics = [
  { label: "Generation", value: "Schema-aware", tone: "text-[color:var(--accent-emerald)]" },
  { label: "Integrity", value: "Key-safe", tone: "text-[color:var(--accent-sky)]" },
  { label: "Delivery", value: "CSV JSON SQL", tone: "text-[color:var(--accent-amber)]" },
];

export const profiles: ProfileConfig[] = [
  {
    name: "Table-Boom",
    role: "Relational table data",
    description: "Key-safe relational datasets with CSV, JSON, and SQL exports.",
    tags: ["tables", "foreign keys"],
    icon: Database,
    selected: true,
    tone: "border-emerald-300/40 text-[color:var(--accent-emerald)]",
  },
  {
    name: "Docu-Boom",
    role: "NoSQL document data",
    description: "MongoDB-style nested JSON and NDJSON collections with document previews.",
    tags: ["json", "ndjson"],
    icon: FileJson,
    selected: false,
    tone: "border-rose-300/40 text-rose-500",
  },
  {
    name: "Graph-Boom",
    role: "Planned graph data",
    description: "Node and edge datasets with labels, properties, and graph validation.",
    tags: ["nodes", "edges"],
    icon: GitBranch,
    selected: false,
    tone: "border-sky-300/40 text-[color:var(--accent-sky)]",
  },
  {
    name: "Masker-Boom",
    role: "Planned masking layer",
    description: "Redaction, tokenization, and integrity-preserving masking for sensitive data.",
    tags: ["masking", "privacy"],
    icon: ShieldCheck,
    selected: false,
    tone: "border-amber-300/40 text-[color:var(--accent-amber)]",
  },
];

export const productCatalog: ProductCatalogItem[] = [
  {
    name: "Table-Boom",
    module: "Relational data",
    status: "achieved",
    summary: "Relational datasets that preserve table structure, keys, references, and export contracts.",
    detail:
      "Built for engineering teams that need production-shaped records for testing, demos, local development, analytics prototypes, and CI fixtures without copying sensitive rows.",
    outputs: ["CSV", "JSON", "SQL", "manifest", "validation report"],
    capabilities: [
      "PostgreSQL DDL parsing",
      "Primary-key and foreign-key preservation",
      "Deterministic generation seeds",
      "Top-row previews and artifact downloads",
    ],
    useCases: ["fintech ledgers", "healthcare records", "commerce orders", "SaaS audit data"],
    icon: Database,
    accent: "from-emerald-300/25 via-cyan-300/10 to-transparent text-[color:var(--accent-emerald)] border-emerald-300/35",
  },
  {
    name: "Docu-Boom",
    module: "NoSQL document data",
    status: "achieved",
    summary: "Nested JSON and NDJSON collections for document databases and event-style applications.",
    detail:
      "Designed for product teams that need realistic object documents, arrays, stable object IDs, and document previews before moving into source-data profiling.",
    outputs: ["JSON", "NDJSON", "manifest", "validation report"],
    capabilities: [
      "Nested object generation",
      "Array fields and stable IDs",
      "Document previews",
      "Collection-level artifacts",
    ],
    useCases: ["customer profiles", "catalog documents", "order events", "activity logs"],
    icon: FileJson,
    accent: "from-cyan-300/25 via-sky-300/10 to-transparent text-[color:var(--accent-cyan)] border-cyan-300/35",
  },
  {
    name: "Graph-Boom",
    module: "Graph data",
    status: "planned",
    summary: "Node and edge generation for connected datasets, relationship graphs, and graph previews.",
    detail:
      "Planned for fraud networks, knowledge graphs, recommendation surfaces, and relationship-heavy datasets where edge validity matters as much as node realism.",
    outputs: ["nodes", "edges", "JSON", "CSV"],
    capabilities: [
      "Node labels and properties",
      "Edge cardinality rules",
      "Graph validation",
      "Graph preview workspace",
    ],
    useCases: ["fraud networks", "recommendations", "knowledge graphs", "ownership maps"],
    icon: GitBranch,
    accent: "from-indigo-300/25 via-sky-300/10 to-transparent text-indigo-500 border-indigo-300/35",
  },
  {
    name: "Masker-Boom",
    module: "Masking and redaction",
    status: "planned",
    summary: "Policy-driven masking for sensitive source data while preserving useful structure.",
    detail:
      "Planned as the privacy layer for teams that need redaction, tokenization, hashing, synthetic replacement, audit reports, and stable joins.",
    outputs: ["masked CSV", "masked JSON", "policy report", "audit log"],
    capabilities: [
      "Sensitive-field classification",
      "Redaction and tokenization policies",
      "Stable synthetic replacement",
      "Privacy validation reports",
    ],
    useCases: ["PII redaction", "tokenized joins", "medical datasets", "customer support data"],
    icon: ShieldCheck,
    accent: "from-amber-300/25 via-emerald-300/10 to-transparent text-[color:var(--accent-amber)] border-amber-300/35",
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
    id: "phase-1",
    phase: "Phase 1",
    status: "achieved",
    title: "Table-Boom relational foundation",
    description:
      "Table-Boom can generate deterministic relational data from PostgreSQL schema files and write validated local artifacts.",
    sections: [
      {
        title: "Delivered",
        empty: "No delivered work recorded yet.",
        items: [
          "PostgreSQL DDL ingestion and normalized schema models.",
          "Relationship-aware generation with primary-key and foreign-key preservation.",
          "CSV, JSON, and SQL artifact export to local disk.",
          "Financial and healthcare use-case profiles plus checked-in CSV datasets.",
          "100k-record benchmark with validation report.",
          "Static Next.js workbench with a reusable component structure.",
        ],
      },
      {
        title: "Maintenance",
        empty: "No maintenance work listed.",
        items: ["Keep Phase 1 benchmark and sample data updated when generation behavior changes."],
      },
    ],
  },
  {
    id: "phase-2",
    phase: "Phase 2",
    status: "achieved",
    title: "Table-Boom scale, API, profiling, and Docu-Boom",
    description:
      "This phase expands Table-Boom scale and access patterns, then adds Docu-Boom document generation for NoSQL use cases.",
    sections: [
      {
        title: "Delivered",
        empty: "No delivered work recorded yet.",
        items: [
          "FastAPI app scaffold with health and readiness endpoints.",
          "Synchronous API generation runs with SQL-backed metadata in Dockerized runs.",
          "Product subscriptions, product generation, table previews, run detail, and downloads.",
          "DataBoom workspace with product navigation, spreadsheet previews, document previews, agent steps, and exports.",
          "Docu-Boom JSON and NDJSON generation with document previews.",
          "Artifact listing and download endpoints for completed local runs.",
          "Optional API-key protection for run and artifact routes.",
          "CLI plan preview and artifact re-validation commands.",
          "Live PostgreSQL schema introspection foundation.",
        ],
      },
      {
        title: "Hardening next",
        empty: "No hardening work listed.",
        items: [
          "Harden generation toward 500k records with chunk-aware validation.",
          "Expand FastAPI run status, validation detail, and long-running job controls.",
          "Add live PostgreSQL profiling and metadata introspection.",
          "Add custom schema upload, custom domain mapping, and saved generation templates.",
        ],
      },
    ],
  },
  {
    id: "phase-3",
    phase: "Phase 3",
    status: "planned",
    title: "LLM-assisted planning, Graph-Boom, and operator UX",
    description:
      "Planning becomes more intelligent while DataBoom gains Graph-Boom support for connected datasets.",
    sections: [
      {
        title: "Planned capabilities",
        empty: "No planned capabilities listed.",
        items: [
          "Add prompt packs, prompt cache keys, and validated planner output schemas.",
          "Add dry-run plan review before generation.",
          "Add Graph-Boom generation for nodes, edges, properties, and graph exports.",
          "Build operator-facing run review, plan review, and graph preview screens.",
        ],
      },
    ],
  },
  {
    id: "phase-4",
    phase: "Phase 4",
    status: "planned",
    title: "Masker-Boom privacy and security hardening",
    description:
      "Sensitive-domain workflows become safer through Masker-Boom policy controls, redaction, tokenization, and privacy validation.",
    sections: [
      {
        title: "Planned capabilities",
        empty: "No planned capabilities listed.",
        items: [
          "Add Masker-Boom policy files for synthetic replacement, hashing, tokenization, and redaction.",
          "Prevent raw sampled values from appearing in logs or reports.",
          "Add audit logs and privacy validation reports.",
        ],
      },
    ],
  },
  {
    id: "phase-5",
    phase: "Phase 5",
    status: "planned",
    title: "Production release and extensibility",
    description:
      "The product becomes deployment-ready with CI, observability, retention controls, and adapter boundaries.",
    sections: [
      {
        title: "Planned capabilities",
        empty: "No planned capabilities listed.",
        items: [
          "Add production deployment guides and CI build verification.",
          "Add health/readiness endpoints, structured logs, and run IDs.",
          "Add adapter boundaries for more databases, object storage, and future export targets.",
        ],
      },
    ],
  },
];
