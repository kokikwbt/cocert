# Data inventory

The package contains synthetic examples and six derived queries with exact proofs: two from ALPI, three from HydSys, and one from MetroPT2. Their attribution and transformations are recorded in [THIRD_PARTY.md](../THIRD_PARTY.md) and `examples/real-small-provenance.json`. The [VLDB evaluation directory](../evaluation/vldb/) also provides saved outcomes and the retained snapshots for one native WMCS audit.

The current primary input inventory is:

| ID | Dataset/provider | Primary count-only queries |
|---|---|---:|
| scania | [Scania Component X, version 3](https://researchdata.se/en/catalogue/dataset/2024-34) | 12,118 |
| metro | [MetroPT2, V2](https://zenodo.org/records/7766691) | 3,717 |
| care | [CARE, v6](https://zenodo.org/records/15846963) | 4,731 |
| xjtu_sy | [XJTU-SY](https://biaowang.tech/xjtu-sy-bearing-datasets/) | 1,886 |
| alpi | [ALPI, version 1](https://data.mendeley.com/datasets/4nhx2x67cd/1) | 5,328 |
| oyicd | [One Year Industrial Component Degradation](https://www.kaggle.com/datasets/inIT-OWL/one-year-industrial-component-degradation) | 3,072 |
| hydsys | [Condition Monitoring of Hydraulic Systems](https://archive.ics.uci.edu/dataset/447/condition+monitoring+of+hydraulic+systems), pressure PS6 | 1,536 |
| wmcs | [Wikimedia Cloud VPS monitoring](https://wikitech.wikimedia.org/wiki/Help:Cloud_VPS_managed_monitoring) | 34,564 |
| Total | Eight datasets, nine scenarios | 66,952 |

This table describes the saved research inputs. The complete input pack is not part of the upload ZIP. Its input counts and hash are in `expected/main-input-inventory.json`; this metadata does not imply that the pack is distributed. Dataset terms for the bundled examples and the provenance of the native WMCS audit appear in [THIRD_PARTY.md](../THIRD_PARTY.md).

Scania and WMCS provide native retained histogram summaries. The other six datasets supply finer real observations from which retained cumulative archives are constructed. OYICD-LE and OYICD-FS are separate signal scenarios within OYICD. This distinction is preserved by separating count-only replay from archive reconstruction and raw-data acquisition.

## Input packs for a complete paper artifact

The following are distinct data products; one does not substitute for another:

1. **A/B/C query packs** reproduce numerical decisions and certificates. They need a fixed version, unique IDs, information condition, bin/selection metadata, and file hashes.
2. **Fine-reference evaluation packs** supply labels or actual boundary allocations for coverage and case-study analyses. Keep them separate from solver inputs.
3. **Retained Parquet archives and request schedules** reproduce storage and I/O measurements. Preserve original compression and row layout rather than reconstructing them from A/B/C counts.
4. **Provider snapshots and preprocessing recipes** reproduce data preparation. Dynamic WMCS endpoints must be tied to the saved snapshot; a later download can differ or become unavailable.

The numerical API accepts externally supplied packs without importing their acquisition code. Dataset acquisition is therefore not a core Python dependency. Full raw-to-paper scripts, full reference packs, and physical archive packs are outside the package. They must be added, with their exact manifests and applicable redistribution notices, before claiming complete paper reproduction.
