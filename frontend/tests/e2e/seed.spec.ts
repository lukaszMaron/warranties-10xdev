import { Buffer } from 'node:buffer';
import { expect, test } from '@playwright/test';

function makeReceiptPdf(): Buffer {
  const content =
    'BT /F1 12 Tf 72 720 Td (Product name: Imported drill Purchase date: 2025-04-03 Seller: Tool shop Payment method: Card) Tj ET';
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
    `<< /Length ${Buffer.byteLength(content, 'ascii')} >>\nstream\n${content}\nendstream`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ];
  const chunks = [Buffer.from('%PDF-1.4\n', 'ascii')];
  const offsets: number[] = [];
  let offset = chunks[0].byteLength;

  for (const [index, object] of objects.entries()) {
    offsets.push(offset);
    const chunk = Buffer.from(`${index + 1} 0 obj\n${object}\nendobj\n`, 'ascii');
    chunks.push(chunk);
    offset += chunk.byteLength;
  }

  const crossReferenceOffset = offset;
  const crossReference = [
    `xref\n0 ${objects.length + 1}\n`,
    '0000000000 65535 f \n',
    ...offsets.map((objectOffset) => `${String(objectOffset).padStart(10, '0')} 00000 n \n`),
  ].join('');
  chunks.push(Buffer.from(crossReference, 'ascii'));
  chunks.push(
    Buffer.from(
      `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${crossReferenceOffset}\n%%EOF`,
      'ascii',
    ),
  );

  return Buffer.concat(chunks);
}

test('PDF import preserves user corrections when the purchase is saved', async ({ page }) => {
  // Provenance: test-plan risk #1.
  await page.goto('/purchases/new');
  await expect(page.getByRole('heading', { name: 'Nowy zakup' })).toBeVisible();

  await page.getByRole('button', { name: /Wybierz plik/ }).setInputFiles({
    name: 'e2e-receipt.pdf',
    mimeType: 'application/pdf',
    buffer: makeReceiptPdf(),
  });
  await expect(page.getByRole('button', { name: 'Odczytaj dokument' })).toBeEnabled();
  await page.getByRole('button', { name: 'Odczytaj dokument' }).click();

  await expect(page.getByRole('status').filter({ hasText: 'Odczyt zakończony' })).toHaveText(
    'Odczyt zakończony. Sprawdź i popraw podpowiedzi.',
  );

  const productName = page.getByRole('textbox', { name: 'Nazwa produktu *' });
  await expect(productName).toHaveValue('Imported drill');
  await expect(page.getByRole('textbox', { name: 'Data zakupu *' })).toHaveValue('2025-04-03');

  const correctedName = `Corrected drill ${Date.now()}`;
  await productName.fill(correctedName);
  await page.getByRole('combobox', { name: 'Rodzaj zakupu *' }).selectOption('private');

  const saveResponsePromise = page.waitForResponse((response) => (
    new URL(response.url()).pathname === '/api/purchases'
    && response.request().method() === 'POST'
  ));
  await page.getByRole('button', { name: 'Zapisz zakup' }).click();
  const saveResponse = await saveResponsePromise;
  expect(saveResponse.ok()).toBeTruthy();

  const savedPurchase = await saveResponse.json() as {
    product_name: string;
    purchase_date: string;
    document_ref: string | null;
  };
  expect(savedPurchase.product_name).toBe(correctedName);
  expect(savedPurchase.purchase_date).toBe('2025-04-03');
  expect(savedPurchase.document_ref).toBeTruthy();

  await expect(page.getByRole('status').filter({ hasText: /^Zapisano zakup\./ })).toBeVisible();
  await expect(page.getByText('Dokument PDF zapisany w profilu.')).toBeVisible();
});
