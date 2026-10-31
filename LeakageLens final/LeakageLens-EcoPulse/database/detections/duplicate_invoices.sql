SELECT
    'INV-DUP-' || a.INVOICE_ID || '-' || b.INVOICE_ID AS FINDING_ID,
    'Duplicate invoice' AS CATEGORY, a.INVOICE_ID,
    CASE WHEN a.PO_ID = b.PO_ID THEN a.PO_ID ELSE a.PO_ID || '|' || b.PO_ID END AS PO_ID,
    CAST(NULL AS VARCHAR(500)) AS PAYMENT_IDS, CAST(NULL AS VARCHAR(500)) AS CREDIT_IDS,
    a.AMOUNT AS EXPECTED_AMOUNT, a.AMOUNT + b.AMOUNT AS OBSERVED_AMOUNT,
    b.AMOUNT AS DIFFERENCE, 0.9600 AS CONFIDENCE,
    'Same supplier and normalized invoice reference; amounts and dates are corroborated before human review.'
        AS EXPLANATION,
    'Compare the source invoice images and supplier ledger before approving or recovering payment.' AS NEXT_ACTION,
    CASE WHEN a.PO_ID = b.PO_ID THEN 'PO references match; ' ELSE 'PO references differ; ' END ||
    CASE WHEN UPPER(TRIM(a.DESCRIPTION)) = UPPER(TRIM(b.DESCRIPTION))
         THEN 'normalized descriptions match.' ELSE 'descriptions differ.' END ||
    ' Amounts: ' || CAST(a.AMOUNT AS VARCHAR(50)) || ' and ' || CAST(b.AMOUNT AS VARCHAR(50)) || '; dates: ' ||
    CAST(a.INVOICE_DATE AS VARCHAR(10)) || ' and ' || CAST(b.INVOICE_DATE AS VARCHAR(10)) ||
    '. Invoice references normalized by removing punctuation.' AS EVIDENCE_TEXT,
    a.INVOICE_ID || '|' || b.INVOICE_ID AS SOURCE_IDS,
    a.SUPPLIER_ID AS SUPPLIER_ID, a.CURRENCY AS CURRENCY
FROM LEAKAGELENS.INVOICES a
JOIN LEAKAGELENS.INVOICES b
  ON a.SUPPLIER_ID = b.SUPPLIER_ID AND b.INVOICE_ID > a.INVOICE_ID
 AND REGEXP_REPLACE(UPPER(a.INVOICE_NUMBER), '[^A-Z0-9]', '') =
     REGEXP_REPLACE(UPPER(b.INVOICE_NUMBER), '[^A-Z0-9]', '')
 AND ABS(a.AMOUNT - b.AMOUNT) <= GREATEST(a.AMOUNT, b.AMOUNT) * {amount_tolerance!f}
 AND b.INVOICE_DATE BETWEEN a.INVOICE_DATE - 45 AND a.INVOICE_DATE + 45
WHERE a.CURRENCY = b.CURRENCY
