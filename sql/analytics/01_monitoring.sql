-- Thresholds are illustrative research rules, not legal reporting thresholds.
-- All timestamps are UTC by convention; exchange_rate means EUR per source unit.
CREATE OR REPLACE VIEW analytics.transaction_facts AS
SELECT t.transaction_id, a.customer_id, t.account_id, t.transaction_timestamp,
       t.transaction_timestamp::date AS transaction_date,
       t.amount, t.currency_id, round(t.amount*t.exchange_rate,2) AS amount_eur,
       t.transaction_direction, t.channel, t.transaction_status,
       tt.transaction_type_name, c.pep_flag, c.customer_risk_level,
       co.iso_code AS destination_country, co.risk_rating AS country_risk,
       co.country_id <> c.residence_country_id AS cross_border
FROM core.transactions t JOIN core.accounts a USING(account_id)
JOIN core.customers c USING(customer_id)
JOIN reference.countries co ON co.country_id=t.country_id
JOIN reference.transaction_types tt USING(transaction_type_id);

CREATE OR REPLACE VIEW analytics.aml_alerts AS
WITH completed AS (SELECT * FROM analytics.transaction_facts WHERE transaction_status='COMPLETED'),
hourly AS (
 SELECT *, count(*) OVER (PARTITION BY account_id ORDER BY transaction_timestamp
    RANGE BETWEEN INTERVAL '1 hour' PRECEDING AND CURRENT ROW) AS hour_count FROM completed
)
SELECT customer_id, account_id, transaction_date, 'STRUCTURING'::text AS rule_code,
       count(*)::bigint AS evidence_count, sum(amount_eur) AS amount_eur
FROM completed WHERE transaction_type_name='CASH_DEPOSIT' AND transaction_direction='INCOMING'
 AND amount_eur >= 8000 AND amount_eur < 10000
GROUP BY customer_id,account_id,transaction_date HAVING count(*) >= 3 AND sum(amount_eur)>=24000
UNION ALL
SELECT customer_id,account_id,transaction_date,'VELOCITY',max(hour_count),sum(amount_eur)
FROM hourly WHERE hour_count >= 10 GROUP BY customer_id,account_id,transaction_date
UNION ALL
SELECT customer_id,account_id,transaction_date,'HIGH_RISK_CORRIDOR',count(*),sum(amount_eur)
FROM completed WHERE cross_border AND country_risk IN ('HIGH','CRITICAL') AND amount_eur>=10000
GROUP BY customer_id,account_id,transaction_date
UNION ALL
SELECT o.customer_id,o.account_id,o.transaction_date,'RAPID_MOVEMENT',count(*),sum(o.amount_eur)
FROM completed o WHERE o.transaction_direction='OUTGOING' AND o.amount_eur>=9000
AND EXISTS (SELECT 1 FROM completed i WHERE i.account_id=o.account_id
 AND i.transaction_direction='INCOMING' AND i.transaction_timestamp < o.transaction_timestamp
 AND i.transaction_timestamp >= o.transaction_timestamp - INTERVAL '1 hour'
 AND o.amount_eur BETWEEN i.amount_eur*0.8 AND i.amount_eur*1.2)
GROUP BY o.customer_id,o.account_id,o.transaction_date;

CREATE OR REPLACE VIEW analytics.customer_features AS
WITH completed AS (SELECT * FROM analytics.transaction_facts WHERE transaction_status='COMPLETED'),
daily AS (SELECT customer_id,transaction_date,count(*) n FROM completed GROUP BY 1,2),
peaks AS (SELECT customer_id,max(n) max_daily_count FROM daily GROUP BY 1)
SELECT c.customer_id, count(f.transaction_id)::bigint AS transaction_count,
 coalesce(sum(f.amount_eur),0) AS total_amount_eur,coalesce(avg(f.amount_eur),0) AS mean_amount_eur,
 coalesce(max(f.amount_eur),0) AS max_amount_eur,
 coalesce(avg((f.cross_border)::int),0) AS cross_border_ratio,
 coalesce(avg((f.country_risk IN ('HIGH','CRITICAL'))::int),0) AS high_risk_country_ratio,
 count(*) FILTER (WHERE f.transaction_type_name='CASH_DEPOSIT' AND f.amount_eur>=8000 AND f.amount_eur<10000) AS near_threshold_cash_count,
 coalesce(p.max_daily_count,0) AS max_daily_count, c.pep_flag::int AS pep_flag
FROM core.customers c LEFT JOIN completed f USING(customer_id) LEFT JOIN peaks p USING(customer_id)
GROUP BY c.customer_id,p.max_daily_count,c.pep_flag;

-- One row per UTC date/country/channel: volumes and alert measures have separate grains.
CREATE OR REPLACE VIEW analytics.dashboard_daily AS
SELECT transaction_date,destination_country,channel,count(*)::bigint AS transaction_count,
 count(*) FILTER (WHERE transaction_status='COMPLETED')::bigint AS completed_count,
 coalesce(sum(amount_eur) FILTER (WHERE transaction_status='COMPLETED'),0) AS completed_amount_eur,
 count(*) FILTER (WHERE cross_border AND transaction_status='COMPLETED')::bigint AS cross_border_count
FROM analytics.transaction_facts GROUP BY 1,2,3;
