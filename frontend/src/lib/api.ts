export type DraftField =
  | "product_name"
  | "purchase_date"
  | "seller"
  | "payment_method";

export interface PreviewDraft {
  product_name: string | null;
  purchase_date: string | null;
  seller: string | null;
  payment_method: string | null;
  warnings: Partial<Record<DraftField, string>>;
}

const apiOrigin = (import.meta.env.PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");

export async function previewPurchase(file: File): Promise<PreviewDraft> {
  const body = new FormData();
  body.set("file", file);
  const response = await fetch(`${apiOrigin}/api/purchases/preview`, {
    method: "POST",
    body,
  });
  const result = (await response.json()) as PreviewDraft | { detail?: string };
  if (!response.ok) {
    const detail = "detail" in result ? result.detail : undefined;
    throw new Error(detail ?? "Nie udało się odczytać dokumentu.");
  }
  return result as PreviewDraft;
}