SELECT
    'UNMATCHED-' || p.PAYMENT_ID AS FINDING_ID,
    'Unmatched payment' AS CATEGORY,
    CAST(NULL AS VARCHAR(100)) AS INVOICE_ID,
    CAST(NULL AS VARCHAR(250)) AS PO_ID,
    p.PAYMENT_ID AS PAYMENT_IDS,
    CAST(NULL AS VARCHAR(500)) AS CREDIT_IDS,
    CAST(0 AS DECIMAL(18,2)) AS EXPECTED_AMOUNT,
    p.AMOUNT AS OBSERVED_AMOUNT,
    p.AMOUNT AS DIFFERENCE,
    0.5500 AS CONFIDENCE,
    'Completed payment has no invoice reference that matches a loaded invoice. The amount is not treated as recoverable.'
        AS EXPLANATION,
    'Review remittance advice and advance-payment records before allocating this payment.' AS NEXT_ACTION,
    'Payment ID, supplier, status, and invoice reference checked against loaded invoices.' AS EVIDENCE_TEXT,
    p.PAYMENT_ID AS SOURCE_IDS,
    p.SUPPLIER_ID AS SUPPLIER_ID, p.CURRENCY AS CURRENCY
FROM LEAKAGELENS.PAYMENTS p
LEFT JOIN LEAKAGELENS.INVOICES i ON i.INVOICE_ID = p.INVOICE_ID
WHERE p.STATUS = 'SETTLED'
  AND p.REVERSAL_OF IS NULL
  AND i.INVOICE_ID IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM LEAKAGELENS.PAYMENTS r
      WHERE r.REVERSAL_OF = p.PAYMENT_ID
  )
