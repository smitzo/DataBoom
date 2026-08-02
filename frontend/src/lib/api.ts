"use client";

export type ApiHealth = {
  status: string;
  service: string;
  version: string;
  environment: string;
  artifact_root: string;
};

export type DemoUser = {
  email: string;
  name: string;
};

export type LoginResponse = {
  token: string;
  user: DemoUser;
};

export type ProductPlan = {
  id: string;
  name: string;
  price: string;
  description: string;
};

export type Product = {
  id: string;
  name: string;
  family: string;
  module: string;
  status: "active" | "planned";
  description: string;
  domain: "general" | "financial" | "healthcare";
  default_row_counts: Record<string, number>;
  output_formats: string[];
  tables: string[];
  features: string[];
  plans: ProductPlan[];
};

export type Subscription = {
  subscription_id: string;
  product_id: string;
  plan_id: string;
  status: "active";
  user_email: string;
  created_at: string;
};

export type GenerationRun = {
  run_id: string;
  status: "completed" | "failed";
  created_at: string;
  completed_at: string | null;
  artifact_dir: string;
  manifest_path: string | null;
  validation_path: string | null;
  domain: string;
  output_formats: string[];
  total_rows: number;
  table_count: number;
  tables: GeneratedTable[];
  validation: {
    passed: boolean;
    checked_tables: string[];
    issues: { code: string; message: string; table_name: string | null }[];
  } | null;
  error: string | null;
};

export type GeneratedTable = {
  table_name: string;
  row_count: number;
  csv_path: string | null;
  json_path: string | null;
  sql_path: string | null;
};

export type RunArtifact = {
  name: string;
  relative_path: string;
  size_bytes: number;
  media_type: string;
  download_url: string;
};

export type ArtifactList = {
  run_id: string;
  artifact_dir: string;
  files: RunArtifact[];
};

export type TablePreview = {
  run_id: string;
  table_name: string;
  columns: string[];
  rows: Record<string, string>[];
};

let cachedApiBaseUrl: string | null = null;

export async function login(email: string, password: string) {
  return apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getMe(token: string) {
  return apiRequest<DemoUser>("/me", {}, token);
}

export async function getProducts() {
  return apiRequest<Product[]>("/products");
}

export async function getProduct(productId: string) {
  return apiRequest<Product>(`/products/${productId}`);
}

export async function getSubscriptions(token: string) {
  return apiRequest<Subscription[]>("/subscriptions", {}, token);
}

export async function subscribeToProduct(token: string, productId: string, planId: string) {
  return apiRequest<Subscription>(
    "/subscriptions",
    {
      method: "POST",
      body: JSON.stringify({ product_id: productId, plan_id: planId }),
    },
    token,
  );
}

export async function createProductRun(
  token: string,
  productId: string,
  payload: { row_counts: Record<string, number>; seed: string; output_formats: string[] },
) {
  return apiRequest<GenerationRun>(
    `/products/${productId}/runs`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function getRuns() {
  return apiRequest<GenerationRun[]>("/runs");
}

export async function getRun(runId: string) {
  return apiRequest<GenerationRun>(`/runs/${runId}`);
}

export async function getRunArtifacts(runId: string) {
  return apiRequest<ArtifactList>(`/runs/${runId}/artifacts`);
}

export async function getTablePreview(runId: string, tableName: string, limit = 10) {
  const params = new URLSearchParams({ table: tableName, limit: String(limit) });
  return apiRequest<TablePreview>(`/runs/${runId}/preview?${params.toString()}`);
}

export async function apiUrl(path: string) {
  const baseUrl = await discoverApiBaseUrl();
  return `${baseUrl}${path}`;
}

export async function discoverApiBaseUrl() {
  if (cachedApiBaseUrl) {
    return cachedApiBaseUrl;
  }

  for (const candidateUrl of apiBaseCandidates()) {
    try {
      const response = await fetch(`${candidateUrl}/health`, { cache: "no-store" });
      if (response.ok) {
        cachedApiBaseUrl = candidateUrl;
        return candidateUrl;
      }
    } catch {
      continue;
    }
  }

  throw new Error("DataBoom API is unavailable. Start the backend with docker compose.");
}

async function apiRequest<T>(path: string, init: RequestInit = {}, token?: string) {
  const baseUrl = await discoverApiBaseUrl();
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    const message = await readErrorMessage(response);
    throw new Error(message);
  }

  return (await response.json()) as T;
}

async function readErrorMessage(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Request failed with ${response.status}`;
  } catch {
    return `Request failed with ${response.status}`;
  }
}

function apiBaseCandidates() {
  const configuredUrl = process.env.NEXT_PUBLIC_DATABOOM_API_URL;
  return Array.from(
    new Set(
      [configuredUrl, "http://localhost:8001", "http://localhost:8000"].filter(
        (url): url is string => Boolean(url),
      ),
    ),
  );
}
