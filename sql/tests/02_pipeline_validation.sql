-- Read-only operational audit: each returned count should be zero.
SELECT 'invalid_amount_or_fx' AS check_name, count(*) AS violations FROM core.transactions
 WHERE amount <= 0 OR amount::text IN ('NaN','Infinity') OR exchange_rate IS NULL
 OR exchange_rate <= 0 OR exchange_rate::text IN ('NaN','Infinity')
UNION ALL
SELECT 'missing_or_future_timestamp',count(*) FROM core.transactions
 WHERE transaction_timestamp IS NULL OR transaction_timestamp > CURRENT_TIMESTAMP
UNION ALL
SELECT 'orphan_account',count(*) FROM core.transactions t LEFT JOIN core.accounts a USING(account_id)
 WHERE a.account_id IS NULL
UNION ALL
SELECT 'transaction_currency_mismatch',count(*) FROM core.transactions t JOIN core.accounts a USING(account_id)
 WHERE t.currency_id <> a.currency_id
UNION ALL
SELECT 'beneficiary_owner_mismatch',count(*) FROM core.transactions t JOIN core.accounts a USING(account_id)
 JOIN core.beneficiaries b USING(beneficiary_id) WHERE b.customer_id <> a.customer_id
UNION ALL
SELECT 'account_balance_below_overdraft',count(*) FROM core.accounts WHERE balance < -overdraft_limit OR overdraft_limit < 0
UNION ALL
SELECT 'invalid_account_dates',count(*) FROM core.accounts WHERE closed_date < opened_date
 OR (account_status='CLOSED') IS DISTINCT FROM (closed_date IS NOT NULL)
UNION ALL
SELECT 'duplicate_transaction_id',count(*) FROM
 (SELECT transaction_id FROM core.transactions GROUP BY transaction_id HAVING count(*)>1) d;
