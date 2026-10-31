SELECT
    'OVER-' || i.INVOICE_ID AS FINDING_ID, 'Overbilling' AS CATEGORY,
    i.INVOICE_ID, po.PO_ID, CAST(NULL AS VARCHAR(500)) AS PAYMENT_IDS,
    CAST(NULL AS VARCHAR(500)) AS CREDIT_IDS,
    po.APPROVED_AMOUNT AS EXPECTED_AMOUNT, i.AMOUNT AS OBSERVED_AMOUNT,
    i.AMOUNT - po.APPROVED_AMOUNT AS DIFFERENCE, 0.9800 AS CONFIDENCE,
    'Invoice amount exceeds its approved purchase order by more than the configured tolerance.'
        AS EXPLANATION,
    'Check PO amendments, delivery records and tax treatment; dispute the unsupported balance.' AS NEXT_ACTION,
    'Approved PO amount, invoice amount, currency and configured tolerance compared in Exasol.'
        AS EVIDENCE_TEXT,
    i.INVOICE_ID || '|' || po.PO_ID AS SOURCE_IDS,
    i.SUPPLIER_ID AS SUPPLIER_ID, i.CURRENCY AS CURRENCY
FROM LEAKAGELENS.INVOICES i
JOIN LEAKAGELENS.PURCHASE_ORDERS po ON po.PO_ID = i.PO_ID
WHERE po.STATUS = 'APPROVED' AND po.CURRENCY = i.CURRENCY
  AND i.AMOUNT - po.APPROVED_AMOUNT > GREATEST(po.APPROVED_AMOUNT, 1) * {amount_tolerance!f}
