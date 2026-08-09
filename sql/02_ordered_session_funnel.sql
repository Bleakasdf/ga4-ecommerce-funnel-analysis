-- A session reaches a stage only when the relevant events occur in order:
-- view_item -> add_to_cart -> begin_checkout -> purchase.
-- traffic_source is a first-user acquisition field in the public GA4 export;
-- it is not session-level attribution.

WITH base AS (
  SELECT
    event_timestamp,
    event_name,
    user_pseudo_id,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS ga_session_id,
    device.category AS device_category,
    CONCAT(traffic_source.source, ' / ', traffic_source.medium) AS first_user_channel
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201125' AND '20210131'
    AND event_name IN ('view_item', 'add_to_cart', 'begin_checkout', 'purchase')
),
session_events AS (
  SELECT
    CONCAT(user_pseudo_id, '-', CAST(ga_session_id AS STRING)) AS session_key,
    ARRAY_AGG(device_category ORDER BY event_timestamp LIMIT 1)[SAFE_OFFSET(0)] AS device_category,
    ARRAY_AGG(first_user_channel ORDER BY event_timestamp LIMIT 1)[SAFE_OFFSET(0)] AS first_user_channel,
    MIN(IF(event_name = 'view_item', event_timestamp, NULL)) AS view_ts,
    MIN(IF(event_name = 'add_to_cart', event_timestamp, NULL)) AS cart_ts,
    MIN(IF(event_name = 'begin_checkout', event_timestamp, NULL)) AS checkout_ts,
    MIN(IF(event_name = 'purchase', event_timestamp, NULL)) AS purchase_ts
  FROM base
  GROUP BY session_key
),
ordered AS (
  SELECT
    *,
    view_ts IS NOT NULL AS reached_view,
    view_ts IS NOT NULL AND cart_ts >= view_ts AS reached_cart,
    view_ts IS NOT NULL AND cart_ts >= view_ts AND checkout_ts >= cart_ts AS reached_checkout,
    view_ts IS NOT NULL AND cart_ts >= view_ts
      AND checkout_ts >= cart_ts AND purchase_ts >= checkout_ts AS reached_purchase
  FROM session_events
),
segments AS (
  SELECT 'Overall' AS segment_type, 'All sessions' AS segment_value,
    * EXCEPT(session_key, device_category, first_user_channel)
  FROM ordered
  UNION ALL
  SELECT 'Device', device_category,
    * EXCEPT(session_key, device_category, first_user_channel)
  FROM ordered
  UNION ALL
  SELECT 'First-user acquisition channel', first_user_channel,
    * EXCEPT(session_key, device_category, first_user_channel)
  FROM ordered
)
SELECT
  segment_type,
  segment_value,
  COUNTIF(reached_view) AS view_sessions,
  COUNTIF(reached_cart) AS cart_sessions,
  COUNTIF(reached_checkout) AS checkout_sessions,
  COUNTIF(reached_purchase) AS purchase_sessions,
  ROUND(SAFE_DIVIDE(COUNTIF(reached_cart), COUNTIF(reached_view)), 4) AS view_to_cart_rate,
  ROUND(SAFE_DIVIDE(COUNTIF(reached_checkout), COUNTIF(reached_cart)), 4) AS cart_to_checkout_rate,
  ROUND(SAFE_DIVIDE(COUNTIF(reached_purchase), COUNTIF(reached_checkout)), 4) AS checkout_to_purchase_rate,
  ROUND(SAFE_DIVIDE(COUNTIF(reached_purchase), COUNTIF(reached_view)), 4) AS view_to_purchase_rate,
  COUNTIF(purchase_ts IS NOT NULL AND NOT reached_purchase) AS purchases_outside_ordered_path
FROM segments
GROUP BY segment_type, segment_value
HAVING segment_type = 'Overall' OR view_sessions >= 500
ORDER BY
  CASE segment_type WHEN 'Overall' THEN 1 WHEN 'Device' THEN 2 ELSE 3 END,
  view_sessions DESC;

