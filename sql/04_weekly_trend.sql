WITH base AS (
  SELECT
    PARSE_DATE('%Y%m%d', event_date) AS event_date,
    event_timestamp,
    event_name,
    user_pseudo_id,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS ga_session_id
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201125' AND '20210131'
    AND event_name IN ('view_item', 'add_to_cart', 'begin_checkout', 'purchase')
),
session_events AS (
  SELECT
    CONCAT(user_pseudo_id, '-', CAST(ga_session_id AS STRING)) AS session_key,
    MIN(event_date) AS session_date,
    MIN(IF(event_name = 'view_item', event_timestamp, NULL)) AS view_ts,
    MIN(IF(event_name = 'add_to_cart', event_timestamp, NULL)) AS cart_ts,
    MIN(IF(event_name = 'begin_checkout', event_timestamp, NULL)) AS checkout_ts,
    MIN(IF(event_name = 'purchase', event_timestamp, NULL)) AS purchase_ts
  FROM base
  GROUP BY session_key
)
SELECT
  DATE_TRUNC(session_date, WEEK(MONDAY)) AS week_start,
  COUNTIF(view_ts IS NOT NULL) AS view_sessions,
  COUNTIF(view_ts IS NOT NULL AND cart_ts >= view_ts) AS cart_sessions,
  COUNTIF(view_ts IS NOT NULL AND cart_ts >= view_ts AND checkout_ts >= cart_ts) AS checkout_sessions,
  COUNTIF(view_ts IS NOT NULL AND cart_ts >= view_ts
    AND checkout_ts >= cart_ts AND purchase_ts >= checkout_ts) AS purchase_sessions,
  ROUND(SAFE_DIVIDE(
    COUNTIF(view_ts IS NOT NULL AND cart_ts >= view_ts
      AND checkout_ts >= cart_ts AND purchase_ts >= checkout_ts),
    COUNTIF(view_ts IS NOT NULL)
  ), 4) AS view_to_purchase_rate,
  DATE_TRUNC(session_date, WEEK(MONDAY)) IN (DATE '2020-11-23', DATE '2021-01-25') AS partial_week
FROM session_events
GROUP BY week_start, partial_week
ORDER BY week_start;
