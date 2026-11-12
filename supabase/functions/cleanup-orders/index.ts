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

function requestAuthorized(req: Request): boolean {
  const supplied = (req.headers.get("x-cleanup-secret") ?? "").trim();
  if (!CLEANUP_SECRET || !supplied || supplied.length !== CLEANUP_SECRET.length) return false;
  let difference = 0;
  for (let index = 0; index < supplied.length; index += 1) {
    difference |= supplied.charCodeAt(index) ^ CLEANUP_SECRET.charCodeAt(index);
  }
  return difference === 0;
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

  let deletedOrders = 0;
  let deletedFiles = 0;
  const storageErrors: string[] = [];
  for (let page = 0; page < 10; page += 1) {
    const cutoff = new Date().toISOString();
    const { data, error } = await supabase
      .from("exhibition_orders")
      .select("id, extra_cards:order_data->_additionalBusinessCardPaths, business_card_original_path, business_card_preview_path")
      .lt("expires_at", cutoff)
      .limit(500);
    if (error) return new Response(JSON.stringify({ error: error.message }), { status: 500 });
    const rows = data ?? [];
    if (!rows.length) break;
    const paths = rows
      .flatMap((row) => {
        const extra = Array.isArray(row.extra_cards) ? row.extra_cards : [];
        const prefix = new RegExp(`^[A-Za-z0-9_-]+/\\d{4}-\\d{2}-\\d{2}/${row.id}/business-card-[2-5]\\.jpg$`);
        return [row.business_card_original_path, row.business_card_preview_path, ...extra.filter(path => typeof path === "string" && prefix.test(path))];
      })
      .filter((path): path is string => Boolean(path));
    for (let index = 0; index < paths.length; index += 100) {
      const group = paths.slice(index, index + 100);
      const { error: removeError } = await supabase.storage.from(BUCKET).remove(group);
      if (removeError) {
        storageErrors.push(removeError.message);
        break;
      }
      deletedFiles += group.length;
    }
    // Retain the references so the next cleanup can retry a partial removal.
    if (storageErrors.length) break;
    const { error: deleteError } = await supabase.from("exhibition_orders")
      .delete().in("id", rows.map((row) => row.id)).lt("expires_at", cutoff);
    if (deleteError) return new Response(JSON.stringify({ error: deleteError.message }), { status: 500 });
    deletedOrders += rows.length;
    if (rows.length < 500) break;
  }

  return new Response(JSON.stringify({ deletedOrders, deletedFiles, storageErrors }), {
    status: storageErrors.length ? 500 : 200,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
});
