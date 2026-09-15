import type { ProductCatalogItem } from "@/data/workbench";
import { productCatalog } from "@/data/workbench";

export type DemoWorkspaceKind = "relational" | "document" | "graph" | "planned";

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
  locale: string;
  rows: number;
  columns: number;
  artifacts: number;
  lastSync: string;
  resources: DemoWorkspaceResource[];
  tableColumns: string[];
  tableRows: DemoTableRow[];
  documents: Record<string, unknown>[];
  description: string;
};

const indiaCustomers = [
  ["Aarav", "Sharma", "male", "Mumbai", "Maharashtra", "400001", "+919810000101", "premium", "active"],
  ["Aditi", "Iyer", "female", "Bengaluru", "Karnataka", "560001", "+919810000102", "enterprise", "active"],
  ["Rohan", "Mehta", "male", "New Delhi", "Delhi", "110001", "+919810000103", "retail", "pending"],
  ["Kavya", "Nair", "female", "Kochi", "Kerala", "682001", "+919810000104", "premium", "active"],
  ["Arjun", "Reddy", "male", "Hyderabad", "Telangana", "500001", "+919810000105", "enterprise", "review"],
  ["Meera", "Banerjee", "female", "Kolkata", "West Bengal", "700001", "+919810000106", "retail", "active"],
  ["Vikram", "Singh", "male", "New Delhi", "Delhi", "110011", "+919810000107", "premium", "active"],
  ["Sneha", "Patel", "female", "Ahmedabad", "Gujarat", "380001", "+919810000108", "enterprise", "pending"],
  ["Rahul", "Deshmukh", "male", "Pune", "Maharashtra", "411001", "+919810000109", "retail", "active"],
  ["Ananya", "Gupta", "female", "Jaipur", "Rajasthan", "302001", "+919810000110", "premium", "active"],
  ["Devika", "Menon", "female", "Chennai", "Tamil Nadu", "600001", "+919810000111", "enterprise", "review"],
  ["Ishaan", "Kapoor", "male", "Chandigarh", "Chandigarh", "160017", "+919810000112", "retail", "active"],
  ["Nisha", "Verma", "female", "Lucknow", "Uttar Pradesh", "226001", "+919810000113", "premium", "pending"],
  ["Siddharth", "Das", "male", "Bhubaneswar", "Odisha", "751001", "+919810000114", "enterprise", "active"],
  ["Priya", "Joshi", "female", "Indore", "Madhya Pradesh", "452001", "+919810000115", "retail", "active"],
  ["Karan", "Malhotra", "male", "Gurugram", "Haryana", "122001", "+919810000116", "premium", "review"],
  ["Riya", "Bose", "female", "Guwahati", "Assam", "781001", "+919810000117", "enterprise", "active"],
  ["Aditya", "Rao", "male", "Visakhapatnam", "Andhra Pradesh", "530001", "+919810000118", "retail", "pending"],
  ["Fatima", "Khan", "female", "Srinagar", "Jammu and Kashmir", "190001", "+919810000119", "premium", "active"],
  ["Neel", "Shah", "male", "Surat", "Gujarat", "395003", "+919810000120", "enterprise", "active"],
] as const;

const tableRows: DemoTableRow[] = indiaCustomers.map(
  ([firstName, lastName, gender, city, state, postalCode, phone, segment, status], index) => ({
    id: String(index + 1),
    full_name: `${firstName} ${lastName}`,
    gender,
    email: `${firstName}.${lastName}.${index + 1}@example.test`.toLowerCase(),
    phone,
    city,
    state,
    postal_code: postalCode,
    segment,
    status,
  }),
);

const documentSamples = [
  customerDocument("65d40a0018af90c100000001", "Olivia", "Bennett", "female", 34, "+12125550101", "New York", "New York", "10001", "gold"),
  customerDocument("65d40a0018af90c100000002", "Ethan", "Brooks", "male", 42, "+12065550102", "Seattle", "Washington", "98101", "standard"),
  customerDocument("65d40a0018af90c100000003", "Sofia", "Ramirez", "female", 29, "+15125550103", "Austin", "Texas", "78701", "platinum"),
  customerDocument("65d40a0018af90c100000004", "Marcus", "Johnson", "male", 51, "+14045550104", "Atlanta", "Georgia", "30303", "gold"),
  customerDocument("65d40a0018af90c100000005", "Emily", "Chen", "female", 38, "+14155550105", "San Francisco", "California", "94105", "platinum"),
  customerDocument("65d40a0018af90c100000006", "Noah", "Williams", "male", 26, "+13125550106", "Chicago", "Illinois", "60601", "standard"),
];

const graphRows: DemoTableRow[] = tableRows.slice(0, 10).map((customer, index) => ({
  id: `customer-${String(index + 1).padStart(6, "0")}`,
  label: "Customer",
  full_name: customer.full_name,
  city: customer.city,
  risk_band: ["low", "low", "medium", "low", "high"][index % 5],
}));

export const demoWorkspaces: DemoWorkspace[] = [
  {
    id: "table-boom",
    name: "Table-Boom",
    kind: "relational",
    module: "Relational data",
    engine: "PostgreSQL",
    database: "commerce_india_demo",
    schema: "public",
    host: "managed demo source",
    locale: "en-IN",
    rows: 3410,
    columns: 42,
    artifacts: 17,
    lastSync: "2m ago",
    resources: [
      { name: "customers", count: 250 },
      { name: "products", count: 80 },
      { name: "orders", count: 750 },
      { name: "order_items", count: 1600 },
      { name: "payments", count: 730 },
    ],
    tableColumns: [
      "id",
      "full_name",
      "gender",
      "email",
      "phone",
      "city",
      "state",
      "postal_code",
      "segment",
      "status",
    ],
    tableRows,
    documents: [],
    description: "Commerce customers generated with relational integrity and India-aware identity and location rules.",
  },
  {
    id: "docu-boom",
    name: "Docu-Boom",
    kind: "document",
    module: "NoSQL document data",
    engine: "Document engine",
    database: "customer_360_demo",
    schema: "collections",
    host: "managed demo source",
    locale: "en-US",
    rows: 3480,
    columns: 24,
    artifacts: 8,
    lastSync: "1m ago",
    resources: [
      { name: "customers", count: 180 },
      { name: "orders", count: 900 },
      { name: "events", count: 2400 },
    ],
    tableColumns: [],
    tableRows: [],
    documents: documentSamples,
    description: "Nested customer documents with coherent US identities, addresses, phones, and stable object identifiers.",
  },
  {
    id: "graph-boom",
    name: "Graph-Boom",
    kind: "graph",
    module: "Graph data",
    engine: "Node and edge engine",
    database: "fraud_network_demo",
    schema: "property graph",
    host: "managed demo source",
    locale: "en-IN",
    rows: 5200,
    columns: 18,
    artifacts: 4,
    lastSync: "4m ago",
    resources: [
      { name: "Customer nodes", count: 500 },
      { name: "Account nodes", count: 900 },
      { name: "Device nodes", count: 700 },
      { name: "OWNS edges", count: 900 },
      { name: "USES_DEVICE edges", count: 2200 },
    ],
    tableColumns: ["id", "label", "full_name", "city", "risk_band"],
    tableRows: graphRows,
    documents: [],
    description: "A validated customer, account, and device network with non-dangling edge references.",
  },
  plannedWorkspace("masker-boom"),
];

export function getDemoWorkspace(productId: string) {
  return demoWorkspaces.find((workspace) => workspace.id === productId) ?? null;
}

export function productCatalogItem(productId: string): ProductCatalogItem | null {
  return productCatalog.find((product) => slugProductName(product.name) === productId) ?? null;
}

function customerDocument(
  id: string,
  firstName: string,
  lastName: string,
  gender: "female" | "male",
  age: number,
  phone: string,
  city: string,
  state: string,
  postalCode: string,
  loyaltyTier: string,
) {
  return {
    _id: id,
    email: `${firstName}.${lastName}@example.test`.toLowerCase(),
    phone,
    status: "active",
    profile: {
      first_name: firstName,
      last_name: lastName,
      gender,
      age,
      loyalty_tier: loyaltyTier,
    },
    addresses: [{ city, state, country: "US", postal_code: postalCode }],
  };
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
    locale: "policy-driven",
    rows: 0,
    columns: 0,
    artifacts: 0,
    lastSync: "planned",
    resources: [],
    tableColumns: [],
    tableRows: [],
    documents: [],
    description: catalogItem?.summary ?? "Planned workspace preview.",
  };
}

function slugProductName(name: string) {
  return name.toLowerCase();
}
