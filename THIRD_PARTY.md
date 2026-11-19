# Sources and attribution

## Bundled derived data

The six records in `examples/real-small.jsonl` and their proofs are derived from the following datasets. The source data were transformed into cumulative histograms and differenced into retained cores A/C and a boundary histogram B. Fine observations and allocations are not included. Selection and identifiers are recorded in `examples/real-small-provenance.json`.

- **ALARM LOGS IN PACKAGING INDUSTRY (ALPI), version 1**, Davide Dalle Pezze, Diego Tosato, Chiara Masiero, Gian Antonio Susto, and Alessandro Beghi (2021). [Provider](https://data.mendeley.com/datasets/4nhx2x67cd/1). [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Condition Monitoring of Hydraulic Systems**, Nikolai Helwig, Eliseo Pignanelli, and Andreas Schütze (2015), UCI Machine Learning Repository. [Provider](https://archive.ics.uci.edu/dataset/447/condition+monitoring+of+hydraulic+systems). [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **MetroPT2: A Benchmark dataset for predictive maintenance (V2)**, Bruno Veloso, João Gama, Rita Ribeiro, and Pedro Pereira (2022), Zenodo. [Provider](https://zenodo.org/records/7766691). [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

These dataset licenses apply to the bundled derived examples independently of the implementation license.

`examples/audit-record/` additionally contains retained cumulative motor-current checkpoints derived from MetroPT2 V2 under the same CC BY 4.0 terms. The request, supplied split count, and certificate describe a constructed 15-minute archive for retrospective investigation; the provider timestamps are preserved. No fine observations are included. `scripts/verify_audit_record.py` reconstructs the query and checks the rational TV bound.

`evaluation/vldb/evidence/wmcs-audit.json` contains eight retained counter snapshots from [Wikimedia Cloud VPS managed monitoring](https://wikitech.wikimedia.org/wiki/Help:Cloud_VPS_managed_monitoring). The record identifies the source metric, intervals, and bin boundaries used to construct the audit query.

## Independent mathematical adapters

AU-DB/AU-DB+ (`baselines/audb.py`) adapt attribute-range arithmetic from Feng et al., *Uncertainty Annotated Databases: A Lightweight Approach for Approximating Certain Answers*, SIGMOD 2021, and subsequent AU-DB work. They are independent implementations for the TV query, rather than a port of the authors' database system. AU-DB+ uses an explicit nonnegative absolute-value tightening.

Density-band (`baselines/density.py`) uses marginal probability ranges and normalized density-band TV bounds, following Fauss and Zoubir, *Old Bands, New Tracks—Revisiting the Band Model for Robust Hypothesis Testing*, IEEE TSP 2018. No third-party source is copied. Interval and Separate are mathematical reference relaxations.

SMT (`baselines/symbolic.py`) independently encodes the shared-variable TV decision using Z3, motivated by the Symb comparison in Feng et al., PVLDB 2023. It is not the original ranking/top-k implementation. Rational SAT allocations are checked directly; UNSAT proofs are not translated into the CoCert portable proof format.

## Python libraries and project code

NumPy, SciPy, Clarabel, Polars, Z3 and pytest are installed from their own distributions, which carry their respective licenses. No installed library binaries are bundled. Exact versions and distribution hashes are recorded in `uv.lock`.

The CoCert implementation and documentation are licensed under the [MIT License](LICENSE). The dataset licenses above apply to the derived examples. Installed dependencies retain their own licenses.
