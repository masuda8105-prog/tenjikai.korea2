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
const CUSTOMER_EDITABLE_STATUSES = ["submitted", "new", "in_progress"];

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
    "Access-Control-Allow-Methods": "GET, POST, PATCH, OPTIONS",
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

function cleanPathSegment(value: unknown, fallback: string): string {
  return String(value ?? "")
    .normalize("NFKC")
    .replace(/[^A-Za-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || fallback;
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

function validateOrder(order: any, staffIntake = false): string | null {
  if (!order || typeof order !== "object") return "注文データがありません。";
  if (!staffIntake && !String(order.customerCompany ?? "").trim()) return "会社名がありません。";
  if (!staffIntake && !String(order.customerName ?? "").trim()) return "氏名がありません。";
  if (!staffIntake && !String(order.customerPhone ?? "").trim()) return "電話番号がありません。";
  if (!Array.isArray(order.items) || order.items.length < 1) return "注文明細がありません。";
  if (order.items.length > 1000) return "1件の注文は1000品番までです。";
  for (const item of order.items) {
    if (!String(item?.c ?? "").trim()) return "品番が空の明細があります。";
    const qty = Number(item?.q ?? 0);
    const unitPrice = Number(item?.p ?? 0);
    if (!Number.isFinite(qty) || qty < 1 || qty > 9999 || (staffIntake && !Number.isInteger(qty))) return "数量が不正です。";
    if (!Number.isFinite(unitPrice) || unitPrice < 0 || (staffIntake && (!Number.isSafeInteger(unitPrice) || unitPrice === 0))) return "価格が不正です。";
  }
  return null;
}

function validSubmissionId(value: unknown): string {
  const id = String(value ?? "").trim().toLowerCase();
  return /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(id) ? id : "";
}

function cleanText(value: unknown, maxLength: number): string {
  return String(value ?? "").trim().slice(0, maxLength);
}

function validEventDate(value: unknown): string | null {
  const date = String(value ?? "").trim();
  return /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : null;
}

async function uploadFile(path: string, file: File): Promise<void> {
  const { error } = await supabase.storage.from(BUCKET).upload(path, await file.arrayBuffer(), {
    contentType: file.type || "application/octet-stream",
    cacheControl: "3600",
    upsert: false,
  });
  if (error) throw new Error(`storage upload failed: ${error.message}`);
}

async function createOrder(req: Request): Promise<Response> {
  if (!originAllowed(req)) return json(req, { error: "origin_not_allowed" }, 403);
  if (!apiKeyAllowed(req)) return json(req, { error: "invalid_api_key" }, 401);

  if (new URL(req.url).searchParams.get("staffIntake") !== "1") return json(req, { error: "staff_order_required" }, 403);
  const staff = await activeStaff(req);
  if (staff instanceof Response) return staff;
  const status = "confirmed";

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

  const validationError = validateOrder(clientOrder, true);
  if (validationError) return json(req, { error: validationError }, 400);
  const total = clientOrder.items.reduce((sum: number, item: { p: unknown; q: unknown }) => sum + Number(item.p) * Number(item.q), 0);
  if (!Number.isSafeInteger(total)) return json(req, { error: "注文合計が範囲外です。" }, 400);
  clientOrder.total = total;
  const clientSubmissionId = validSubmissionId(clientOrder.clientSubmissionId);
  if (!clientSubmissionId) return json(req, { error: "client_submission_id_invalid" }, 400);

  const { data: existing, error: existingError } = await supabase
    .from("exhibition_orders")
    .select("id, public_token, order_no, order_data, status, created_at, updated_at, expires_at, business_card_original_path, business_card_preview_path")
    .eq("client_submission_id", clientSubmissionId)
    .maybeSingle();
  if (existingError && existingError.code !== "42703") {
    return json(req, { error: existingError.message }, 500);
  }
  if (existing) {
    if (!existing.order_data?._staffIntake) return json(req, { error: "submission_conflict" }, 409);
    return json(req, {
      id: existing.id,
      receipt: await makeReceiptCredential(existing.id, existing.public_token),
      total: Number(existing.order_data?.total) || 0,
      orderNo: existing.order_no,
      status: existing.status,
      createdAt: existing.created_at,
      updatedAt: existing.updated_at,
      expiresAt: existing.expires_at,
      hasBusinessCard: Boolean(existing.business_card_original_path || existing.business_card_preview_path),
      duplicatePrevented: true,
    });
  }

  const original = form.get("businessCardOriginal");
  const preview = form.get("businessCardPreview");
  const originalFile = original instanceof File && original.size > 0 ? original : null;
  const previewFile = preview instanceof File && preview.size > 0 ? preview : null;
  const additionalCards = form.getAll("additionalBusinessCards");
  if (additionalCards.length > 4 || additionalCards.some(file =>
    !(file instanceof File) || file.type !== "image/jpeg" || file.size === 0 || file.size > 5 * 1024 * 1024
  )) {
    return json(req, { error: "名刺は合計5枚まで、追加画像は1枚5MB以下のJPEGにしてください。" }, 400);
  }

  if (originalFile && (!originalFile.type.startsWith("image/") || originalFile.size > 15 * 1024 * 1024)) {
    return json(req, { error: "名刺の元画像は15MB以下の画像ファイルにしてください。" }, 400);
  }
  if (previewFile && (!previewFile.type.startsWith("image/") || previewFile.size > 5 * 1024 * 1024)) {
    return json(req, { error: "名刺プレビュー画像が大きすぎます。" }, 400);
  }

  const id = crypto.randomUUID();
  const token = randomToken(32);
  const receipt = await makeReceiptCredential(id, token);
  const { data: orderNo, error: orderNumberError } = await supabase.rpc("next_korea_staff_order_no");
  if (orderNumberError || typeof orderNo !== "string" || !/^K-\d{4,}$/.test(orderNo)) {
    return json(req, { error: "staff_order_number_unavailable" }, 503);
  }
  const createdAt = new Date().toISOString();
  const order = {
    ...clientOrder,
    _staffIntake: true,
    _additionalBusinessCardPaths: [],
    staffName: staff.name,
    v: 10,
    clientSubmissionId,
    eventId: cleanText(clientOrder.eventId, 120) || "korea-exhibition",
    eventName: cleanText(clientOrder.eventName, 240),
    eventDate: validEventDate(clientOrder.eventDate),
    eventDay: Math.max(1, Math.min(99, Number(clientOrder.eventDay) || 1)),
    orderNo,
    status,
    createdAt,
    date: createdAt,
  };
  const storageDate = order.eventDate || createdAt.slice(0, 10);
  const basePath = `${cleanPathSegment(order.eventId, "korea-exhibition")}/${storageDate}/${id}`;
  const originalPath = originalFile
    ? `${basePath}/original-${cleanFileName(originalFile.name).replace(/\.[^.]+$/, "")}.${extensionFor(originalFile)}`
    : null;
  const previewPath = previewFile ? `${basePath}/preview.jpg` : null;
  const additionalPaths = additionalCards.map((_, index) => `${basePath}/business-card-${index + 2}.jpg`);
  order._additionalBusinessCardPaths = additionalPaths;
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
    for (const [index, file] of additionalCards.entries()) {
      const path = additionalPaths[index];
      await uploadFile(path, file as File);
      uploaded.push(path);
    }

    const expiresAt = new Date(Date.now() + RETENTION_DAYS * 86400000).toISOString();
    const { error } = await supabase.from("exhibition_orders").insert({
      id,
      public_token: token,
      order_no: orderNo,
      order_data: order,
      status,
      assigned_to: staff.id,
      assigned_name: staff.name,
      completed_at: createdAt,
      client_submission_id: clientSubmissionId,
      event_id: order.eventId,
      event_name: order.eventName || null,
      event_date: order.eventDate,
      event_day: order.eventDay,
      business_card_original_path: originalPath,
      business_card_preview_path: previewPath,
      expires_at: expiresAt,
      updated_at: createdAt,
    });
    if (error?.code === "23505") {
      if (uploaded.length) await supabase.storage.from(BUCKET).remove(uploaded);
      const { data: raced } = await supabase
        .from("exhibition_orders")
        .select("id, public_token, order_no, order_data, status, created_at, updated_at, expires_at, business_card_original_path, business_card_preview_path")
        .eq("client_submission_id", clientSubmissionId)
        .maybeSingle();
      if (raced) {
        if (!raced.order_data?._staffIntake) return json(req, { error: "submission_conflict" }, 409);
        return json(req, {
          id: raced.id,
          receipt: await makeReceiptCredential(raced.id, raced.public_token),
          total: Number(raced.order_data?.total) || 0,
          orderNo: raced.order_no,
          status: raced.status,
          createdAt: raced.created_at,
          updatedAt: raced.updated_at,
          expiresAt: raced.expires_at,
          hasBusinessCard: Boolean(raced.business_card_original_path || raced.business_card_preview_path),
          duplicatePrevented: true,
        });
      }
    }
    if (error) throw new Error(`database insert failed: ${error.message}`);

    return json(req, {
      id,
      receipt,
      total,
      orderNo,
      status,
      createdAt,
      updatedAt: createdAt,
      expiresAt,
      hasBusinessCard: Boolean(originalPath || previewPath || additionalPaths.length),
    }, 201);
  } catch (error) {
    if (uploaded.length) await supabase.storage.from(BUCKET).remove(uploaded).catch(() => undefined);
    console.error(error);
    return json(req, { error: error instanceof Error ? error.message : "create_failed" }, 500);
  }
}

function requestedFile(form: FormData, name: string): File | null {
  const value = form.get(name);
  return value instanceof File && value.size > 0 ? value : null;
}

function validateBusinessCardFiles(originalFile: File | null, previewFile: File | null): string | null {
  if (originalFile && (!originalFile.type.startsWith("image/") || originalFile.size > 15 * 1024 * 1024)) {
    return "名刺の元画像は15MB以下の画像ファイルにしてください。";
  }
  if (previewFile && (!previewFile.type.startsWith("image/") || previewFile.size > 5 * 1024 * 1024)) {
    return "名刺プレビュー画像が大きすぎます。";
  }
  return null;
}

async function updateOrder(req: Request): Promise<Response> {
  if (!originAllowed(req)) return json(req, { error: "origin_not_allowed" }, 403);
  if (!apiKeyAllowed(req)) return json(req, { error: "invalid_api_key" }, 401);

  let form: FormData;
  try {
    form = await req.formData();
  } catch {
    return json(req, { error: "multipart_form_required" }, 400);
  }

  const token = cleanText(form.get("token"), 100);
  const expectedUpdatedAt = cleanText(form.get("expectedUpdatedAt"), 80);
  const orderRaw = form.get("order");
  if (!/^[A-Za-z0-9_-]{30,80}$/.test(token)) return json(req, { error: "invalid_token" }, 400);
  if (!expectedUpdatedAt || Number.isNaN(new Date(expectedUpdatedAt).getTime())) {
    return json(req, { error: "expected_updated_at_required" }, 400);
  }
  if (typeof orderRaw !== "string") return json(req, { error: "order_json_required" }, 400);

  let clientOrder: any;
  try {
    clientOrder = JSON.parse(orderRaw);
  } catch {
    return json(req, { error: "invalid_order_json" }, 400);
  }
  const validationError = validateOrder(clientOrder);
  if (validationError) return json(req, { error: validationError }, 400);

  const { data: current, error: readError } = await supabase
    .from("exhibition_orders")
    .select("id, public_token, order_no, client_submission_id, order_data, status, revision_count, requires_resend, event_id, event_name, event_date, event_day, business_card_original_path, business_card_preview_path, created_at, updated_at, expires_at")
    .eq("public_token", token)
    .maybeSingle();
  if (readError) return json(req, { error: readError.message }, 500);
  if (!current) return json(req, { error: "order_not_found" }, 404);
  if (new Date(current.expires_at).getTime() <= Date.now()) return json(req, { error: "order_expired" }, 410);
  if (!CUSTOMER_EDITABLE_STATUSES.includes(current.status)) {
    return json(req, { error: "order_already_confirmed", status: current.status, editable: false }, 409);
  }
  if (current.updated_at !== expectedUpdatedAt) {
    return json(req, { error: "order_changed", status: current.status, updatedAt: current.updated_at }, 409);
  }

  const originalFile = requestedFile(form, "businessCardOriginal");
  const previewFile = requestedFile(form, "businessCardPreview");
  const fileError = validateBusinessCardFiles(originalFile, previewFile);
  if (fileError) return json(req, { error: fileError }, 400);
  const removeBusinessCard = form.get("removeBusinessCard") === "1";
  const revisionNumber = Number(current.revision_count || 0) + 1;
  const editedAt = new Date().toISOString();
  const currentData = current.order_data && typeof current.order_data === "object" ? current.order_data : {};
  const editableKeys = [
    "lang", "distributor", "staffName", "customerCompany", "customerName", "customerPhone",
    "shippingAddress", "notes", "priceMode", "currency", "total", "items",
  ];
  const mergedOrder: Record<string, unknown> = { ...currentData };
  for (const key of editableKeys) {
    if (Object.hasOwn(clientOrder, key)) mergedOrder[key] = clientOrder[key];
  }
  Object.assign(mergedOrder, {
    v: Math.max(10, Number(currentData.v || clientOrder.v || 10)),
    orderNo: current.order_no,
    clientSubmissionId: current.client_submission_id || currentData.clientSubmissionId || clientOrder.clientSubmissionId,
    eventId: current.event_id || currentData.eventId || clientOrder.eventId,
    eventName: current.event_name || currentData.eventName || clientOrder.eventName,
    eventDate: current.event_date || currentData.eventDate || clientOrder.eventDate,
    eventDay: current.event_day || currentData.eventDay || clientOrder.eventDay,
    createdAt: currentData.createdAt || current.created_at,
    date: currentData.date || current.created_at,
    status: current.status,
    _revisionCount: revisionNumber,
    _lastRevisionAt: editedAt,
    _lastRevisionBy: "お客様",
    _lastRevisionReason: "お客様による注文内容の修正",
  });

  const storageDate = String(current.event_date || current.created_at).slice(0, 10);
  const basePath = `${cleanPathSegment(current.event_id, "korea-exhibition")}/${storageDate}/${current.id}`;
  const newOriginalPath = originalFile
    ? `${basePath}/customer-edit-${revisionNumber}-original-${cleanFileName(originalFile.name).replace(/\.[^.]+$/, "")}.${extensionFor(originalFile)}`
    : null;
  const newPreviewPath = previewFile ? `${basePath}/customer-edit-${revisionNumber}-preview.jpg` : null;
  const uploaded: string[] = [];

  try {
    if (originalFile && newOriginalPath) {
      await uploadFile(newOriginalPath, originalFile);
      uploaded.push(newOriginalPath);
    }
    if (previewFile && newPreviewPath) {
      await uploadFile(newPreviewPath, previewFile);
      uploaded.push(newPreviewPath);
    }

    const nextOriginalPath = removeBusinessCard ? null : (newOriginalPath || current.business_card_original_path);
    const nextPreviewPath = removeBusinessCard ? null : (newPreviewPath || current.business_card_preview_path);
    const { data: updatedRows, error: updateError } = await supabase
      .from("exhibition_orders")
      .update({
        order_data: mergedOrder,
        business_card_original_path: nextOriginalPath,
        business_card_preview_path: nextPreviewPath,
        revision_count: revisionNumber,
        revision_reason: "お客様による注文内容の修正",
      })
      .eq("id", current.id)
      .eq("updated_at", expectedUpdatedAt)
      .in("status", CUSTOMER_EDITABLE_STATUSES)
      .select("id, public_token, order_no, status, revision_count, created_at, updated_at, expires_at, business_card_original_path, business_card_preview_path");
    if (updateError) throw new Error(`database update failed: ${updateError.message}`);
    const updated = updatedRows?.[0];
    if (!updated) {
      if (uploaded.length) await supabase.storage.from(BUCKET).remove(uploaded);
      const { data: latest } = await supabase
        .from("exhibition_orders")
        .select("status, updated_at")
        .eq("id", current.id)
        .maybeSingle();
      return json(req, {
        error: CUSTOMER_EDITABLE_STATUSES.includes(latest?.status ?? "") ? "order_changed" : "order_already_confirmed",
        status: latest?.status ?? current.status,
        updatedAt: latest?.updated_at ?? current.updated_at,
        editable: CUSTOMER_EDITABLE_STATUSES.includes(latest?.status ?? ""),
      }, 409);
    }

    const oldPaths = [current.business_card_original_path, current.business_card_preview_path]
      .filter((path): path is string => Boolean(path))
      .filter((path) => path !== nextOriginalPath && path !== nextPreviewPath);
    if (oldPaths.length) await supabase.storage.from(BUCKET).remove([...new Set(oldPaths)]).catch(() => undefined);

    await Promise.allSettled([
      supabase.from("order_revisions").insert({
        order_id: current.id,
        event_id: current.event_id,
        revision_number: revisionNumber,
        changed_by: null,
        changed_by_name: "お客様",
        change_reason: "お客様による注文内容の修正",
        status_before: current.status,
        status_after: current.status,
        before_data: currentData,
        after_data: mergedOrder,
        batch_id_before: null,
      }),
      supabase.from("order_activity_logs").insert({
        order_id: current.id,
        event_id: current.event_id,
        action: "customer_order_updated",
        performed_by: null,
        performed_by_name: "お客様",
        details: { revision_number: revisionNumber, business_card_changed: Boolean(originalFile || previewFile || removeBusinessCard) },
      }),
    ]);

    return json(req, {
      id: updated.id,
      token: updated.public_token,
      orderNo: updated.order_no,
      status: updated.status,
      revisionCount: updated.revision_count,
      createdAt: updated.created_at,
      updatedAt: updated.updated_at,
      expiresAt: updated.expires_at,
      editable: true,
      hasBusinessCard: Boolean(updated.business_card_original_path || updated.business_card_preview_path),
    });
  } catch (error) {
    if (uploaded.length) await supabase.storage.from(BUCKET).remove(uploaded).catch(() => undefined);
    console.error(error);
    return json(req, { error: error instanceof Error ? error.message : "update_failed" }, 500);
  }
}

async function signedUrl(path: string | null): Promise<string> {
  if (!path) return "";
  const { data, error } = await supabase.storage.from(BUCKET).createSignedUrl(path, SIGNED_URL_SECONDS);
  if (error) throw new Error(`signed url failed: ${error.message}`);
  return data?.signedUrl ?? "";
}

const ORDER_UUID = /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;
const RECEIPT_SIGNATURE = /^[0-9a-f]{64}$/;

async function activeStaff(req: Request): Promise<{ id: string; name: string } | Response> {
  const jwt = req.headers.get("Authorization")?.match(/^Bearer (\S+)$/i)?.[1];
  if (!jwt) return json(req, { error: "staff_login_required" }, 401);
  const { data: { user }, error } = await supabase.auth.getUser(jwt);
  if (error || !user) return json(req, { error: "staff_login_required" }, 401);
  const staff = await supabase.from("exhibition_staff").select("display_name").eq("user_id", user.id).eq("active", true).maybeSingle();
  if (staff.error) return json(req, { error: "staff_lookup_failed" }, 500);
  if (!staff.data) return json(req, { error: "staff_required" }, 403);
  return { id: user.id, name: staff.data.display_name };
}

async function receiptKey(token: string) {
  return crypto.subtle.importKey("raw", new TextEncoder().encode(token), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}

function receiptMessage(id: string) {
  return new TextEncoder().encode(`customer-receipt-v1:${id}`);
}

async function makeReceiptCredential(id: string, token: string) {
  const bytes = new Uint8Array(await crypto.subtle.sign("HMAC", await receiptKey(token), receiptMessage(id)));
  return `${id}.${Array.from(bytes, byte => byte.toString(16).padStart(2, "0")).join("")}`;
}

async function customerReceipt(req: Request, url: URL): Promise<Response> {
  const issuing = url.searchParams.has("issueReceiptFor");
  const [id, signature, extra] = issuing
    ? [url.searchParams.get("issueReceiptFor") ?? "", "", undefined]
    : (url.searchParams.get("receipt") ?? "").split(".");
  if (!ORDER_UUID.test(id) || (!issuing && (!RECEIPT_SIGNATURE.test(signature) || extra !== undefined))) {
    return json(req, { error: "order_not_found" }, 404);
  }

  if (issuing) {
    const staff = await activeStaff(req);
    if (staff instanceof Response) return staff;
  }

  const { data, error } = await supabase.from("exhibition_orders")
    .select("id, public_token, order_no, order_data, created_at")
    .eq("id", id).neq("status", "deleted").gt("expires_at", new Date().toISOString()).maybeSingle();
  if (error) return json(req, { error: "read_failed" }, 500);
  if (!data?.public_token) return json(req, { error: "order_not_found" }, 404);

  // A receipt signature cannot be used as the legacy order edit token.
  if (issuing) return json(req, { receipt: await makeReceiptCredential(data.id, data.public_token) });
  const bytes = Uint8Array.from(signature.match(/../g) ?? [], part => parseInt(part, 16));
  if (!await crypto.subtle.verify("HMAC", await receiptKey(data.public_token), bytes, receiptMessage(data.id))) {
    return json(req, { error: "order_not_found" }, 404);
  }
  const items = Array.isArray(data.order_data?.items) ? data.order_data.items : [];
  return json(req, {
    orderNo: data.order_no,
    createdAt: data.created_at,
    items: items.map((item: { c?: unknown; n?: unknown; p?: unknown; q?: unknown }) => ({
      c: typeof item?.c === "string" ? item.c : "",
      n: Array.isArray(item?.n) ? item.n.map(value => typeof value === "string" ? value : "") : typeof item?.n === "string" ? item.n : "",
      p: Number(item?.p) || 0,
      q: Number(item?.q) || 0,
    })),
  });
}

async function getOrder(req: Request): Promise<Response> {
  if (!originAllowed(req)) return json(req, { error: "origin_not_allowed" }, 403);
  if (!apiKeyAllowed(req)) return json(req, { error: "invalid_api_key" }, 401);

  const url = new URL(req.url);
  if (url.searchParams.has("receipt") || url.searchParams.has("issueReceiptFor")) return customerReceipt(req, url);
  const token = (url.searchParams.get("token") ?? "").trim();
  if (!/^[A-Za-z0-9_-]{30,80}$/.test(token)) return json(req, { error: "invalid_token" }, 400);

  const { data, error } = await supabase
    .from("exhibition_orders")
    .select("id, public_token, order_no, order_data, status, revision_count, assigned_name, business_card_original_path, business_card_preview_path, created_at, updated_at, expires_at")
    .eq("public_token", token)
    .maybeSingle();
  if (error) return json(req, { error: error.message }, 500);
  if (!data) return json(req, { error: "order_not_found" }, 404);
  if (data.order_data?._staffIntake) return json(req, { error: "order_not_found" }, 404);
  if (new Date(data.expires_at).getTime() <= Date.now()) return json(req, { error: "order_expired" }, 410);

  try {
    const [businessCardOriginalUrl, businessCardPreviewUrl] = await Promise.all([
      signedUrl(data.business_card_original_path),
      signedUrl(data.business_card_preview_path),
    ]);
    return json(req, {
      id: data.id,
      token: data.public_token,
      orderNo: data.order_no,
      updatedAt: data.updated_at,
      editable: CUSTOMER_EDITABLE_STATUSES.includes(data.status),
      order: {
        ...data.order_data,
        orderNo: data.order_no,
        status: data.status,
        assignedName: data.assigned_name ?? "",
        revisionCount: data.revision_count ?? 0,
        createdAt: data.order_data?.createdAt ?? data.created_at,
      },
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
  if (req.method === "PATCH") return updateOrder(req);
  if (req.method === "GET") return getOrder(req);
  return json(req, { error: "method_not_allowed" }, 405);
});
