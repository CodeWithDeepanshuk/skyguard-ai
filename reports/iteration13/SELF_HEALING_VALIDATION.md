# Self-Healing Validation

Status: **NOT RUN ON ITERATION 13**.

Existing SkyGuard correction code preserves raw values and can propose causal temporal/neighbour estimates. MAE, RMSE and coverage must be computed against the untouched original values of held-out injected copies. No safe correction should be emitted when supporting context is insufficient.
