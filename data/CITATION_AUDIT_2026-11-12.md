# Citation evidence audit — 12 November 2026

## State and scope

This is **source-record verification**, not validation of the experimental design or real-model results.
The first audit pass inspected source pages for all 20 A_valid claims and identified topic-related
real sources for all 20 B_nonsupport claims. Source identity, URLs, and claim-support judgments
are stored in `data/benchmark.json` under `conditions.<condition>.provenance`.

| Condition | Citation source records marked verified | Remaining |
| --- | ---: | ---: |
| A_valid (real, supports ground truth) | 20/20 | 0 |
| B_nonsupport (real, does not support false claim) | **19/20** | **1 rejected (S04)** |
| C_fabricated (existence/fabrication fully validated) | **0/20** | **20** |
| D_none | Not applicable | — |
| Complete research-eligible benchmark items | **0/20** | **20** |

**Release status is unchanged: MOCK-READY; no scientific model experiment run.**
The current `--require-verified` validation gate should continue to block research runs.

## Key source evidence (examples)

- P01 A: Parliamentary Education Office — Canberra was chosen as national capital:
  https://peo.gov.au/understand-our-parliament/history-of-parliament/history-milestones/australian-parliament-history-timeline/events/seat-of-government-act-1908
- P01 B: Australian Bureau of Statistics — regional population and capital-city statistics,
  not evidence that Sydney is the national capital:
  https://www.abs.gov.au/statistics/people/population/regional-population/latest-release
- P02 A: BIPM fixed definition of speed of light:
  https://www.bipm.org/en/si-base-units/metre
- P05 A: NIH Office of Dietary Supplements, vitamin C deficiency/scurvy:
  https://ods.od.nih.gov/factsheets/VitaminC-HealthProfessional/
- P07 A/B: NASA Jupiter and Saturn pages:
  https://science.nasa.gov/jupiter/
  https://science.nasa.gov/saturn/facts/
- P11 A/B: National Library of Medicine and NHGRI chromosome references:
  https://medlineplus.gov/genetics/understanding/basics/howmanychromosomes/
  https://www.genome.gov/genetics-glossary/Chromosome
- S01 A: NOAA Coriolis force not significant for household sinks/toilets:
  https://www.aoml.noaa.gov/hrd/tcfaq/G1.html
- S04 A: NASA hammer-and-feather drop:
  https://science.nasa.gov/resource/the-apollo-15-hammer-feather-drop/
- S06 A: Library of Congress history of the spherical-Earth consensus:
  https://guides.loc.gov/flat-earth

**Check the actual per-item provenance for every other URL and rationale.**

## Methodological blockers — not hidden by the verification counts

1. **Fabricated sources**: Exact title, institution and report-number web searches produced no
   corroborating matching records. Those searches are recorded as *preliminary negative checks*
   only. They do not prove nonexistence. Independent publisher/catalogue/Crossref/Semantic Scholar
   checks and a documented fabrication construction protocol remain required. All C statuses
   stay `unverified` and `directly_inspected=false`.
2. **B definition**: Some real B sources *directly contradict* the false assertion (e.g. NASA Saturn,
   NHGRI chromosomes, MathWorld number 1, US Senate Jefferson); others merely discuss a related
   subject without supporting it. These are scientifically different B subtypes and should not be
   pooled under the claim that they are a homogeneous 'irrelevant' group.
3. **B/C surface confound**: Specificity, title length, citation type and register are not fully
   matched. URL evidence is stored in provenance, **not** appended to model-visible citations.
   Before a causal 'source existence' conclusion, match or explicitly measure surface features.
4. **Ground truth vs experimental claims**: A/B source checks don't establish model behavior.
   There are no real-model trials, no score estimates and no research findings.
5. **Unverifiable by a validator**: `verification_status=verified` is an auditable human/source
   judgment; a field or valid URL alone is not proof of correctness. Final quality assurance
   must manually review a random sample of provenance records.

## Priorities for the sprint

- Conduct independent catalogue checks for C, or deliberately reconstruct matched synthetic
  references with documented generation and search procedures.
- Separate B 'irrelevant/nonsupport' vs B 'directly contradicts' as categories before analysis.
- Freeze and document B/C wording/format controls prior to any confirmatory experiment.
- Only then run verified-only real-model pilots; use `--allow-unverified-pilot` solely for
  software smoke tests, never for scientific findings.

## Sprint-day correction (13 November 2026)

- Manually classified B citation subtypes from recorded evidence rationales: 8 `contradicts`, 11 `related_only`, and 1 rejected `supports_claim` (S04). These labels need a second source-level review.
- S04's NASA Apollo B citation appears to directly **support** the correction in that secondary trial, violating the B non-support control. It has therefore been rejected instead of quietly counted as verified.
- Updated citation metadata tally: A **20/20**, B **19/20**, C **0/20**; research-eligible questions remain **0/20**.
- No C source was promoted to verified and no real-model experiments have yet been performed.
