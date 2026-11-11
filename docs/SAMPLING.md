# Finite records and sampling

A CoCert query asks which empirical contrasts follow from a retained finite record. Its exact certificates are valid for that record independently of a sampling model. Analysts can additionally specify count-aware tolerances when making inferences under a supplied sampling contract.

Stationary controls using 64 native small-count window geometries give 37.9% and 41.3% positive rates at a fixed empirical threshold of 0.1, for IID and conditional-permutation draws respectively. Increasing counts reduces these rates. These are generated controls, not additional measured datasets.

The optional `cocert.window_thresholds` module accepts one threshold per window. Its `calibrated` function uses a Hoeffding subset/side/window union bound. `cocert.paired_calibration.paired_calibrated` directly concentrates two-sample TV by bounded differences. Both use the fixed nominal bin count and count schedule; unknown totals use core count lower bounds. `decide` constructs exact certificates, and `cocert.verify_window_thresholds` checks them using only the standard library.

Calibration requires integral observation counts, a nonnegative effect tolerance, an error probability strictly between zero and one, and a positive integer grid denominator. A supplied split count must be integral and feasible. The complete threshold, including the effect tolerance, rounds upward on that grid. Verification binds the proof to the requested thresholds through `epsilon=...` and to the externally supplied split count through `total=...`.

At alpha 0.05, no calibrated positive appears among the 49,152 null draws. Each 8,192-draw condition has a 95% Hoeffding upper endpoint of 1.51%; zero observed triggers do not prove a zero population rate. On the eight integral-count measured datasets, sharing adds 124 answers at effect tolerance zero and 46 at 0.1, with no WMCS positives under this calibration.

The subset-union guarantee assumes independent categorical sampling or uniform sampling without replacement. The paired guarantee assumes independent categorical observations. Its `block_size` argument supports independent blocks with a known maximum length, allowing arbitrary dependence within each block. Overlapping comparisons need no mutual independence. Guarantees apply per query with fixed bins, endpoints and a category-independent count schedule. The measured sensor-data comparisons are threshold-sensitivity analyses because these sampling contracts have not been established for those records.

At native template counts all calibrated thresholds are at least one, so a positive is impossible. Such vacuous requests number 640/8,192 per null at eight times the counts and zero at 64 times the counts. In the zero-effect real-data study, all thresholds are at least one on 25,924 WMCS and all 1,886 XJTU-SY queries. The absence of positives must be read alongside this loss of power.

The paired-sample replay uses the same 58,115 measured requests and count information. Sharing adds 150 answers at effect tolerance zero and 48 at 0.1, compared with 124 and 46 under subset-union calibration. At 0.1, the paired policy reduces all-vacuous requests from 28,381 to 19,419. WMCS has no positives with either policy.

A generated 10,240-record grid retains eight native window geometries and varies population effect, observation count, and independent-block length. With IID observations, effect 0.4 and 64 times the counts, both CoCert and Separate sharp reach 81.6% with paired calibration versus 74.6% with subset union. With known blocks of length 16 and 512 times the counts, power is 70.7% at effect 0.4 and 100% at 0.8. The corresponding block policy has zero positives in 4,096 composite-null draws. These finite simulation results characterize the stated sampling models.

The block contract cannot be inferred from histograms alone. In an exact four-outcome stress example, each half repeats one independent fair binary category 6,400 times. Applying IID calibration yields a population-null trigger probability of 1/2. Supplying the known block size returns four exact low-contrast witnesses. The same realized-record certificate remains computationally sound throughout; its population interpretation depends on the sampling contract.

Across all 60 aggregate cells using the IID subset-union/paired policies or the supplied-block policy, both processors give identical positive sets, with zero sharing additions and no unresolved answers. These single-shift controls isolate the calibration policy. Sharing gains on measured records are evaluated separately above.

The complete grids, configurations, and check summaries are included in `expected/reviewer-diagnostics/calibration-power-*`. The large-count controls appear as `integer-large-*`. Their manifest lists the included files and hashes. These are inspection tables; full empirical input packs are separate data products.
