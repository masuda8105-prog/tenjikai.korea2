import { createClient } from "npm:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SERVICE_ROLE_KEY = getServiceKey();
const BUCKET = Deno.env.get("BUSINESS_CARD_BUCKET") ?? "business-cards";
const RETENTION_DAYS = Math.max(1, Math.min(90, Number(Deno.env.get("ORDER_RETENTION_DAYS") ?? "14")));
const SIGNED_URL_SECONDS = Math.max(300, Math.min(86400, Number(Deno.env.get("SIGNED_URL_SECONDS") ?? "3600")));
const ALLOWED_ORIGINS = (Deno.env.get("ALLOWED_ORIGINS") ?? "")
  .split(",")
  .map((value) => value.trim().replace(/\/$/, ""))
  .filter(Boolean);

const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
  auth: { persistSession: false, autoRefreshToken: false },
});

function readKeyMap(name: string): string[] {
  const raw = Deno.env.get(name) ?? "";
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return [];
    return Object.values(parsed).filter((value): value is string => typeof value === "string" && value.length > 0);
  } catch {
    return [];
  }
}

function getServiceKey(): string {
  const modern = readKeyMap("SUPABASE_SECRET_KEYS");
  return modern[0] ?? Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
}

function acceptedPublicKeys(): string[] {
  const keys = readKeyMap("SUPABASE_PUBLISHABLE_KEYS");
  const legacy = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
  if (legacy) keys.push(legacy);
  return [...new Set(keys)];
}

function apiKeyAllowed(req: Request): boolean {
  const supplied = (req.headers.get("apikey") ?? "").trim();
  return Boolean(supplied && acceptedPublicKeys().includes(supplied));
}

function normalizedOrigin(req: Request): string {
  return (req.headers.get("origin") ?? "").replace(/\/$/, "");
}

function originAllowed(req: Request): boolean {
  const origin = normalizedOrigin(req);
  return Boolean(origin && ALLOWED_ORIGINS.includes(origin));
}

function corsHeaders(req: Request): HeadersInit {
  const origin = normalizedOrigin(req);
  return {
    "Access-Control-Allow-Origin": originAllowed(req) ? origin : "null",
    "Access-Control-Allow-Headers": "apikey, authorization, content-type",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Vary": "Origin",
  };
}

function json(req: Request, body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...corsHeaders(req),
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

function randomToken(bytes = 32): string {
  const values = crypto.getRandomValues(new Uint8Array(bytes));
  let binary = "";
  for (const value of values) binary += String.fromCharCode(value);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/g, "");
}

function cleanFileName(name: string): string {
  return name.normalize("NFKC").replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 100) || "business-card";
}

function extensionFor(file: File): string {
  const byMime: Record<string, string> = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
    "image/heif": "heif",
  };
  if (byMime[file.type]) return byMime[file.type];
  const found = cleanFileName(file.name).match(/\.([A-Za-z0-9]{2,5})$/);
  return found?.[1]?.toLowerCase() ?? "jpg";
}

function validateOrder(order: any): string | null {
  if (!order || typeof order !== "object") return "注文データがありません。";
  if (!String(order.customerCompany ?? "").trim()) return "会社名がありません。";
  if (!String(order.customerName ?? "").trim()) return "氏名がありません。";
  if (!String(order.customerPhone ?? "").trim()) return "電話番号がありません。";
  if (!Array.isArray(order.items) || order.items.length < 1) return "注文明細がありません。";
  if (order.items.length > 1000) return "1件の注文は1000品番までです。";
  for (const item of order.items) {
    if (!String(item?.c ?? "").trim()) return "品番が空の明細があります。";
    const qty = Number(item?.q ?? 0);
    const unitPrice = Number(item?.p ?? 0);
    if (!Number.isFinite(qty) || qty < 1 || qty > 9999) return "数量が不正です。";
    if (!Number.isFinite(unitPrice) || unitPrice < 0) return "価格が不正です。";
  }
  return null;
}

async function uploadFile(path: string, file: File): Promise<void> {
  const { error } = await supabase.storage.from(BUCKET).upload(path, await file.arrayBuffer(), {
    contentType: file.type || "application/octet-stream",
    cacheControl: "3600",
    upsert: false,
  });
  if (error) throw new Error(`storage upload failed: ${error.message}`);
}

function fallbackOrderNo(): string {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
  });
  const parts = Object.fromEntries(formatter.formatToParts(new Date()).map((part) => [part.type, part.value]));
  const suffix = crypto.randomUUID().replaceAll("-", "").slice(0, 5).toUpperCase();
  return `K${parts.year}${parts.month}${parts.day}-${suffix}`;
}

async function issueOrderNo(): Promise<string> {
  const { data, error } = await supabase.rpc("next_korea_order_no");
  if (!error && typeof data === "string" && data) return data;
  console.warn("next_korea_order_no unavailable; using collision-resistant fallback", error?.message ?? "");
  return fallbackOrderNo();
}

async function createOrder(req: Request): Promise<Response> {
  if (!originAllowed(req)) return json(req, { error: "origin_not_allowed" }, 403);
  if (!apiKeyAllowed(req)) return json(req, { error: "invalid_api_key" }, 401);

  let form: FormData;
  try {
    form = await req.formData();
  } catch {
    return json(req, { error: "multipart_form_required" }, 400);
  }

  const orderRaw = form.get("order");
  if (typeof orderRaw !== "string") return json(req, { error: "order_json_required" }, 400);

  let clientOrder: any;
  try {
    clientOrder = JSON.parse(orderRaw);
  } catch {
    return json(req, { error: "invalid_order_json" }, 400);
  }

  const validationError = validateOrder(clientOrder);
  if (validationError) return json(req, { error: validationError }, 400);

  const original = form.get("businessCardOriginal");
  const preview = form.get("businessCardPreview");
  const originalFile = original instanceof File && original.size > 0 ? original : null;
  const previewFile = preview instanceof File && preview.size > 0 ? preview : null;

  if (originalFile && (!originalFile.type.startsWith("image/") || originalFile.size > 15 * 1024 * 1024)) {
    return json(req, { error: "名刺の元画像は15MB以下の画像ファイルにしてください。" }, 400);
  }
  if (previewFile && (!previewFile.type.startsWith("image/") || previewFile.size > 5 * 1024 * 1024)) {
    return json(req, { error: "名刺プレビュー画像が大きすぎます。" }, 400);
  }

  const id = crypto.randomUUID();
  const token = randomToken(32);
  const orderNo = await issueOrderNo();
  const createdAt = new Date().toISOString();
  const order = {
    ...clientOrder,
    v: 9,
    orderNo,
    status: "new",
    createdAt,
    date: createdAt,
  };
  const basePath = id;
  const originalPath = originalFile
    ? `${basePath}/original-${cleanFileName(originalFile.name).replace(/\.[^.]+$/, "")}.${extensionFor(originalFile)}`
    : null;
  const previewPath = previewFile ? `${basePath}/preview.jpg` : null;
  const uploaded: string[] = [];

  try {
    if (originalFile && originalPath) {
      await uploadFile(originalPath, originalFile);
      uploaded.push(originalPath);
    }
    if (previewFile && previewPath) {
      await uploadFile(previewPath, previewFile);
      uploaded.push(previewPath);
    }

    const expiresAt = new Date(Date.now() + RETENTION_DAYS * 86400000).toISOString();
    const { error } = await supabase.from("exhibition_orders").insert({
      id,
      public_token: token,
      order_no: orderNo,
      order_data: order,
      status: "new",
      business_card_original_path: originalPath,
      business_card_preview_path: previewPath,
      expires_at: expiresAt,
    });
    if (error) throw new Error(`database insert failed: ${error.message}`);

    return json(req, {
      id,
      token,
      orderNo,
      status: "new",
      createdAt,
      expiresAt,
      hasBusinessCard: Boolean(originalPath || previewPath),
    }, 201);
  } catch (error) {
    if (uploaded.length) await supabase.storage.from(BUCKET).remove(uploaded).catch(() => undefined);
    console.error(error);
    return json(req, { error: error instanceof Error ? error.message : "create_failed" }, 500);
  }
}

async function signedUrl(path: string | null): Promise<string> {
  if (!path) return "";
  const { data, error } = await supabase.storage.from(BUCKET).createSignedUrl(path, SIGNED_URL_SECONDS);
  if (error) throw new Error(`signed url failed: ${error.message}`);
  return data?.signedUrl ?? "";
}

async function getOrder(req: Request): Promise<Response> {
  if (!originAllowed(req)) return json(req, { error: "origin_not_allowed" }, 403);
  if (!apiKeyAllowed(req)) return json(req, { error: "invalid_api_key" }, 401);

  const url = new URL(req.url);
  const token = (url.searchParams.get("token") ?? "").trim();
  if (!/^[A-Za-z0-9_-]{30,80}$/.test(token)) return json(req, { error: "invalid_token" }, 400);

  const { data, error } = await supabase
    .from("exhibition_orders")
    .select("order_data, status, assigned_name, business_card_original_path, business_card_preview_path, expires_at")
    .eq("public_token", token)
    .maybeSingle();
  if (error) return json(req, { error: error.message }, 500);
  if (!data) return json(req, { error: "order_not_found" }, 404);
  if (new Date(data.expires_at).getTime() <= Date.now()) return json(req, { error: "order_expired" }, 410);

  try {
    const [businessCardOriginalUrl, businessCardPreviewUrl] = await Promise.all([
      signedUrl(data.business_card_original_path),
      signedUrl(data.business_card_preview_path),
    ]);
    return json(req, {
      order: { ...data.order_data, status: data.status, assignedName: data.assigned_name ?? "" },
      status: data.status,
      expiresAt: data.expires_at,
      signedUrlExpiresIn: SIGNED_URL_SECONDS,
      businessCardOriginalUrl,
      businessCardPreviewUrl,
    });
  } catch (error) {
    console.error(error);
    return json(req, { error: error instanceof Error ? error.message : "read_failed" }, 500);
  }
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    if (!originAllowed(req)) return new Response("forbidden", { status: 403, headers: corsHeaders(req) });
    return new Response("ok", { headers: corsHeaders(req) });
  }
  if (!SUPABASE_URL || !SERVICE_ROLE_KEY) return json(req, { error: "server_not_configured" }, 500);
  if (req.method === "POST") return createOrder(req);
  if (req.method === "GET") return getOrder(req);
  return json(req, { error: "method_not_allowed" }, 405);
});
