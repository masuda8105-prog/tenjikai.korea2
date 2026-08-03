import { createClient } from "npm:@supabase/supabase-js@2";

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

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SERVICE_ROLE_KEY = readKeyMap("SUPABASE_SECRET_KEYS")[0] ?? Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
const CLEANUP_SECRET = Deno.env.get("CLEANUP_SECRET") ?? "";

function acceptedPublicKeys(): string[] {
  const keys = readKeyMap("SUPABASE_PUBLISHABLE_KEYS");
  const legacy = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
  if (legacy) keys.push(legacy);
  return [...new Set(keys)];
}

function requestAuthorized(req: Request): boolean {
  const apiKey = (req.headers.get("apikey") ?? "").trim();
  const legacySecret = (req.headers.get("x-cleanup-secret") ?? "").trim();
  return Boolean((apiKey && acceptedPublicKeys().includes(apiKey)) || (CLEANUP_SECRET && legacySecret === CLEANUP_SECRET));
}
const BUCKET = Deno.env.get("BUSINESS_CARD_BUCKET") ?? "business-cards";
const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
  auth: { persistSession: false, autoRefreshToken: false },
});

Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response(JSON.stringify({ error: "method_not_allowed" }), { status: 405 });
  if (!requestAuthorized(req)) {
    return new Response(JSON.stringify({ error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json; charset=utf-8" } });
  }
  if (!SUPABASE_URL || !SERVICE_ROLE_KEY) {
    return new Response(JSON.stringify({ error: "server_not_configured" }), { status: 500 });
  }

  const { data, error } = await supabase
    .from("exhibition_orders")
    .select("id, business_card_original_path, business_card_preview_path")
    .lt("expires_at", new Date().toISOString())
    .limit(500);
  if (error) return new Response(JSON.stringify({ error: error.message }), { status: 500 });

  const rows = data ?? [];
  const paths = rows
    .flatMap((row) => [row.business_card_original_path, row.business_card_preview_path])
    .filter((path): path is string => Boolean(path));

  if (paths.length) {
    const { error: removeError } = await supabase.storage.from(BUCKET).remove(paths);
    if (removeError) return new Response(JSON.stringify({ error: removeError.message }), { status: 500 });
  }
  if (rows.length) {
    const { error: deleteError } = await supabase.from("exhibition_orders").delete().in("id", rows.map((row) => row.id));
    if (deleteError) return new Response(JSON.stringify({ error: deleteError.message }), { status: 500 });
  }

  return new Response(JSON.stringify({ deletedOrders: rows.length, deletedFiles: paths.length }), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
});
