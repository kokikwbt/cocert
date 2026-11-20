# Data inventory

The package contains synthetic examples and five derived queries with exact proofs, including two from ALPI, two from HydSys, and one from MetroPT2. Their attribution and transformations are recorded in [THIRD_PARTY.md](../THIRD_PARTY.md) and `examples/real-small-provenance.json`. The [VLDB evaluation directory](../evaluation/vldb/) also provides saved outcomes and the retained snapshots for one native WMCS audit.

## Download the source data

Set up PdMData in a separate checkout. Use the Python version pinned by PdMData and its locked dependencies in that checkout. The following downloads HydSys. Replace `hydsys` with the PdMData ID for the dataset you need.

```sh
git clone https://github.com/kokikwbt/predictive-maintenance.git
cd predictive-maintenance
uv sync --locked --no-default-groups
uv run --locked --no-default-groups python scripts/download.py hydsys
```

The default destination is `data/raw/<pdmdata-id>/` inside the PdMData checkout. Add `--print-command` to inspect the configured download source before transferring data. [PdMData setup and download options](https://github.com/kokikwbt/predictive-maintenance/blob/main/docs/usage.md#downloading-datasets)

OYICD uses Kaggle. Authenticate in the PdMData checkout and then use the same downloader. [Kaggle authentication in PdMData](https://github.com/kokikwbt/predictive-maintenance/blob/main/docs/usage.md#kaggle-authentication)

```sh
uv run --locked --no-default-groups kaggle auth login
uv run --locked --no-default-groups python scripts/download.py oyicd
```

The WMCS experiments use retained snapshots collected through the Prometheus API. For a full rerun, use the frozen snapshot inputs from the original evaluation. The bundled WMCS audit includes the checkpoint counts needed to replay its certificate. [WMCS monitoring documentation](https://wikitech.wikimedia.org/wiki/Help:Cloud_VPS_managed_monitoring)

## Dataset inventory

| CoCert ID | Dataset/provider | PdMData ID | Primary count-only queries |
|---|---|---|---:|
| scania | [Scania Component X, version 3](https://researchdata.se/en/catalogue/dataset/2024-34) | `scania_x` | 12,118 |
| metro | [MetroPT2, V2](https://zenodo.org/records/7766691) | `metropt2` | 3,717 |
| care | [CARE, v6](https://zenodo.org/records/15846963) | `care` | 4,731 |
| xjtu_sy | [XJTU-SY](https://biaowang.tech/xjtu-sy-bearing-datasets/) | `xjtu_sy` | 1,886 |
| alpi | [ALPI, version 1](https://data.mendeley.com/datasets/4nhx2x67cd/1) | `alpi` | 5,328 |
| oyicd | [One Year Industrial Component Degradation](https://www.kaggle.com/datasets/inIT-OWL/one-year-industrial-component-degradation) | `oyicd` | 3,072 |
| hydsys | [Condition Monitoring of Hydraulic Systems](https://archive.ics.uci.edu/dataset/447/condition+monitoring+of+hydraulic+systems), pressure PS6 | `hydsys` | 1,536 |
| wmcs | [Wikimedia Cloud VPS monitoring](https://wikitech.wikimedia.org/wiki/Help:Cloud_VPS_managed_monitoring) | — | 34,564 |
| Total | Eight datasets, nine scenarios | — | 66,952 |

The [count-only input inventory](../expected/main-input-inventory.json) records the workload and its digest. For the provenance of the bundled derived examples, see [data attribution](../THIRD_PARTY.md).

Scania and WMCS provide native retained histogram summaries. The other six datasets supply finer real observations from which retained cumulative archives are constructed. OYICD-LE and OYICD-FS are separate signal scenarios within OYICD. This distinction is preserved by separating count-only replay from archive reconstruction and raw-data acquisition.

## Inputs for full runs

The evaluation guide describes the included records. Dataset-wide runs require the corresponding frozen inputs. [Saved evaluation records](../evaluation/vldb/)

| Input | Required for |
| --- | --- |
| Count-only query pack and a separate split-total file | Re-running the methods with the same information |
| Fine-reference records for the identical bins and window endpoints | Recomputing certification recall and paired intervals |
| Retained Parquet archives and request schedules | Measuring archive size and end-to-end runtime |
| Original frozen provider snapshots | Reconstructing inputs, including the time-specific WMCS archives |
