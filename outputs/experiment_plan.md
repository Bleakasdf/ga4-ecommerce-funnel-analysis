# Experiment plan: product-view to purchase funnel

## Decision

Test the highest-evidence product-page friction hypothesis after instrumentation QA. Randomize eligible viewed sessions 50/50 at the user level and keep assignment sticky across sessions.

## Sizing

- Baseline purchase conversion per viewed session: **4.71%**.
- Target detectable effect: **10% relative lift** to **5.18%**.
- Two-sided alpha: **5%**; power: **80%**.
- Required sample: **33,264 viewed sessions per arm** (**66,528 total**).
- At the historical rate of **834 viewed sessions/day**, the lower-bound runtime is about **80 days** before adding a full-business-cycle constraint.

## Measurement contract

- Primary outcome: purchase conversion per assigned user among eligible product viewers.
- Diagnostic: add-to-cart conversion, add-to-cart error rate, and CTA exposure.
- Guardrails: revenue per viewed session, checkout error rate, and refund rate if available.
- Segments are diagnostic only; the overall treatment effect is the decision metric.

## Decision rule

Ship only if the predeclared primary metric improves, guardrails stay within agreed bounds, instrumentation is stable, and the result survives a full business cycle. Otherwise iterate or stop; do not select a winning segment after the fact.

## Caveats

This is an analytical design, not an executed experiment. The sample calculation uses the committed aggregate baseline and a normal approximation for two independent proportions. Recalculate with user-level exposure data before launch and adjust for repeat sessions or other clustering.

