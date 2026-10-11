# SWELL · concept card

*Written by an AI (Claude by Anthropic, used through Claude Code) for X-WOW, at the project owner's direction. Every check named below is an AI review.*

**Hook:** an expansion microscope designed to check every gel against chicken muscle.
**What it does:** a hydrogel swells the specimen 4–10× so a microscope with a 3D-printed stage and stock glass
objectives could resolve detail below the light's limit; chicken myofibrils expanded with it carry sarcomeres whose
spacing, read before and after, would report how much each fibril grew; a desk design with simulations and a red-team
test, given away free, never built.
**Status:** added to the board's data on 2026-10-10. SWELL predates the charter. This card applies the charter's gate to it
honestly, and it **has not passed the gate**: an AI review (2026-10-10; an AI told to read as a sceptical specialist) scored principle 12 a fail, and principles 2 and 4 are untested or weak. It stays
on the board, labelled, as the first invention and the yardstick later cards are measured against.

## Quick checks
- Shockingly cheap: unknown yet. Only 3 of the build's 31 lines have a price read on a supplier page; together they
  come to ≥ £214 (site numbers `swell.build_floor`, `swell.build_n_priced`, `swell.build_n`); the other 28 are not yet
  priced (`swell.build_n_est`), so no total exists and SWELL is not compared with any instrument's price (D-78,
  2026-10-11; the comparison with UK public contract awards that stood here returns once every line is priced).
- Scientifically wow: proposed and untested: a per-myofibril expansion factor and a whole-gel strain map from a
  supermarket reference specimen, so far only on synthetic gels.
- Feels like 2030: a 3D-printed stage with stock glass objectives; automated fluidics and self-checking QC are
  proposed, not designed or tested. Most build lines are not yet priced, so the guard (every part orderable today with a
  real price) isn't met yet.

## Gate 0: seeing core
Pass as a design: it is designed to image below the diffraction limit (in original-specimen units) and to measure its
own expansion. Neither is tested.

## The twelve principles
1. Shockingly cheap: untested (most lines not yet priced; see Quick checks). *(Changed 2026-10-11 from "pass,
   estimated": D-78 keeps unpriced lines out of every total.)*
2. Scientifically wow: untested (nothing measured; simulated on our own synthetic gels and one red-team gel).
3. Clever beats expensive: pass ("grow the sample, not the glass").
4. It checks itself: weak (proposed; on red-team gel S3 it flagged none of the planted under- or over-expanded
   patches).
5. £5 first step: weak (measure a chicken with a laser; the Class 2 pointer we priced costs £17.83 with VAT, site
   number `laser.cost`).
6. Runs where support is thin: weak (needs an equipped lab for the gels).
7. Honest by construction: pass (evidence bar, failures published).
8. A recipe: pass (open design).
9. Credit first: pass (prior art page).
10. Fun: pass.
11. Unique: pass with credit, narrow (AI review, 2026-10-10). New as far as our searches found: chicken
    myofibrils embedded in the gel as a free reference spread through its volume, each long fibril's sarcomere period
    read twice (label-free, by differential phase contrast, before expansion; stained after), giving that fibril's own
    axial expansion factor with no lithography, pre-label or super-resolution pre-image. Not new, and credited:
    before/after imaging of the same specimen to measure expansion and distortion (Chen, Tillberg & Boyden 2015;
    Tillberg et al. 2016; Chozinski et al. 2016; Pesce et al. 2019); before/after intrinsic rulers as QC (Vanheusden et
    al. 2020); label-free before/after expansion measurement (VISTA; Miao, Lin, Qian & Wei 2022); sarcomeres as
    expansion reporters (Sheard et al. 2019; Sheard 2021 thesis); expanded isolated vertebrate myofibrils with an A-band
    ruler (Migliore 2022 thesis); in-gel rulers and deformation maps (Scheible & Tinnefeld 2018 preprint; GelMap,
    Damstra et al. 2023); cheap optics for expanded samples (Zhang, Chang et al. 2016).
12. Feels like 2030: **fail** (AI review, 2026-10-10). Expansion read on cheap optics (2016), printed
    microscopes with 40×/0.65 objectives and epifluorescence (2020) and super-resolution on low-cost open microscopes
    (2024) already exist, and the one-button automation has no design yet.

## Prior-art search
Ten dated searches, 2026-10-10: docs/design/prior_art.md in the SWELL download. The AI review ran 17 more
on 2026-10-10 and found the credits listed under principle 11.

## Expert
AI reviews only: fresh Claude agents, not people, and never an expert, independent or peer review.
- 2026-10-09: an AI review session reran the download; its points, and what changed, are on the SWELL page ("Tested
  harder").
- 2026-10-10: three AI reviews of the page and the download, role-playing a builder, a sceptical expansion-microscopy
  academic and an IP-and-overclaim reader (a fourth reviewed the videos page, not SWELL).
- 2026-10-10: the charter's expert test, run as an AI review: an AI role-playing a sceptical specialist in expansion and quantitative
  light microscopy. Principle 11: pass with credit, narrow. Principle 12: fail. Closest existing things: Sheard et al.
  2019 (a sarcomere-period expansion factor in expanded heart cells) for the ruler, GelMap (Damstra et al. 2023) for
  whole-gel QC, and Migliore 2022 for the specimen. Not unsafe; not unoriginal, narrowly; naive where the page treated a
  myofibril's expansion as the gel's (dense protein structures can expand less than the gel around them: Damstra et
  al. 2022; Sheard 2021), which the page now says.

Verdict carried here: a proposed reference specimen, untested on real images. It has not passed the charter's gate.
