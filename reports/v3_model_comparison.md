# OmniBet Lab v3A hybrid model comparison

Walk-forward comparison between the v2 rolling Poisson baseline and the new v3A hybrid logistic layer.

## Summary

- Matches tested: **211**
- Baseline 1X2 accuracy: **0.474**
- Hybrid 1X2 accuracy: **0.460**
- Delta 1X2 accuracy: **-0.014**
- Baseline Over 2.5 accuracy: **0.517**
- Hybrid Over 2.5 accuracy: **0.540**
- Delta Over 2.5 accuracy: **+0.024**
- Baseline log loss: **1.044**
- Hybrid log loss: **1.028**
- Delta log loss: **-0.016**

## Interpretation

The hybrid model adds rolling-form stats, rank priors, and calibrated logistic probabilities on top of Poisson-style score features. The goal is not merely higher accuracy; lower log loss and better-calibrated confidence are more important for value betting.

If the hybrid improves log loss but not raw accuracy, it may still be valuable for odds comparison. If it improves neither, the next step is more data and stronger features, not a more complex GUI.