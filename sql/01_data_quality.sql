-- Source: bigquery-public-data.ga4_obfuscated_sample_ecommerce
-- The source covers 2020-11-01 to 2021-01-31. This check shows that
-- add_to_cart is absent on 18 dates, so the comparable analysis window
-- starts on 2020-11-25, the first day after the final gap.

WITH calendar AS (
  SELECT day
  FROM UNNEST(GENERATE_DATE_ARRAY(DATE '2020-11-01', DATE '2021-01-31')) AS day
),
daily AS (
  SELECT
    PARSE_DATE('%Y%m%d', event_date) AS day,
    COUNTIF(event_name = 'view_item') AS view_item_events,
    COUNTIF(event_name = 'add_to_cart') AS add_to_cart_events,
    COUNTIF(event_name = 'begin_checkout') AS begin_checkout_events,
    COUNTIF(event_name = 'purchase') AS purchase_events
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
  GROUP BY day
)
SELECT
  calendar.day,
  COALESCE(view_item_events, 0) AS view_item_events,
  COALESCE(add_to_cart_events, 0) AS add_to_cart_events,
  COALESCE(begin_checkout_events, 0) AS begin_checkout_events,
  COALESCE(purchase_events, 0) AS purchase_events,
  COALESCE(add_to_cart_events, 0) = 0 AS missing_add_to_cart
FROM calendar
LEFT JOIN daily USING (day)
ORDER BY calendar.day;

