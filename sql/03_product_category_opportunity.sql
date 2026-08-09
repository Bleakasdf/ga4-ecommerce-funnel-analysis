-- Item categories are consistent for view_item and add_to_cart, but not for
-- later checkout events. Category opportunity is therefore estimated at the
-- view-to-cart step and translated into purchases with the overall downstream
-- cart-to-purchase rate. This is a scenario, not a forecast.

WITH funnel_events AS (
  SELECT
    event_timestamp,
    event_name,
    user_pseudo_id,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS ga_session_id
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201125' AND '20210131'
    AND event_name IN ('view_item', 'add_to_cart', 'begin_checkout', 'purchase')
),
session_funnel AS (
  SELECT
    CONCAT(user_pseudo_id, '-', CAST(ga_session_id AS STRING)) AS session_key,
    MIN(IF(event_name = 'view_item', event_timestamp, NULL)) AS view_ts,
    MIN(IF(event_name = 'add_to_cart', event_timestamp, NULL)) AS cart_ts,
    MIN(IF(event_name = 'begin_checkout', event_timestamp, NULL)) AS checkout_ts,
    MIN(IF(event_name = 'purchase', event_timestamp, NULL)) AS purchase_ts
  FROM funnel_events
  GROUP BY session_key
),
benchmark AS (
  SELECT
    SAFE_DIVIDE(COUNTIF(view_ts IS NOT NULL AND cart_ts >= view_ts),
      COUNTIF(view_ts IS NOT NULL)) AS view_to_cart_rate,
    SAFE_DIVIDE(
      COUNTIF(view_ts IS NOT NULL AND cart_ts >= view_ts
        AND checkout_ts >= cart_ts AND purchase_ts >= checkout_ts),
      COUNTIF(view_ts IS NOT NULL AND cart_ts >= view_ts)
    ) AS cart_to_purchase_rate
  FROM session_funnel
),
item_events AS (
  SELECT
    event_timestamp,
    event_name,
    user_pseudo_id,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS ga_session_id,
    COALESCE(NULLIF(item.item_category, ''), 'Unknown') AS product_category
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`,
  UNNEST(items) AS item
  WHERE _TABLE_SUFFIX BETWEEN '20201125' AND '20210131'
    AND event_name IN ('view_item', 'add_to_cart')
),
session_category AS (
  SELECT
    CONCAT(user_pseudo_id, '-', CAST(ga_session_id AS STRING)) AS session_key,
    product_category,
    MIN(IF(event_name = 'view_item', event_timestamp, NULL)) AS view_ts,
    MIN(IF(event_name = 'add_to_cart', event_timestamp, NULL)) AS cart_ts
  FROM item_events
  GROUP BY session_key, product_category
),
category_metrics AS (
  SELECT
    product_category,
    COUNTIF(view_ts IS NOT NULL) AS view_sessions,
    COUNTIF(view_ts IS NOT NULL AND cart_ts >= view_ts) AS cart_sessions
  FROM session_category
  GROUP BY product_category
  HAVING view_sessions >= 300
)
SELECT
  product_category,
  view_sessions,
  cart_sessions,
  ROUND(SAFE_DIVIDE(cart_sessions, view_sessions), 4) AS view_to_cart_rate,
  ROUND(benchmark.view_to_cart_rate, 4) AS overall_benchmark_rate,
  GREATEST(0, ROUND(view_sessions * benchmark.view_to_cart_rate - cart_sessions)) AS scenario_extra_carts,
  GREATEST(0, ROUND(
    (view_sessions * benchmark.view_to_cart_rate - cart_sessions)
    * benchmark.cart_to_purchase_rate
  )) AS scenario_extra_purchases
FROM category_metrics
CROSS JOIN benchmark
ORDER BY scenario_extra_purchases DESC, view_sessions DESC;

