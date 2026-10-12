<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="src/assets/img/brand/xwow-logo-dark-192.png">
    <img src="src/assets/img/brand/xwow-logo-192.png" alt="X-WOW logo: a microscope in a four-colour ring above the word X-WOW" width="224" height="192">
  </picture>
</p>

# X-WOW: inventions to steal, happily

The source of [x-wow.com](https://x-wow.com/). Test address: https://khcy82dyc2.github.io/x-wow/

X-WOW gives away free, open inventions for seeing more closely. Invention #1 is **SWELL**, an automated expansion microscope designed to be cheap (most of its parts are not yet priced). It is designed on paper and simulated. The wet-lab protocol, the mechanical and fluidic designs and the instrument software are not written yet, and nobody has built one. Whoever builds it is welcome to claim the success.

## Build
```
python build.py
```
This needs Python 3.9+ with its standard library, and git (the Inventions board dates each file from the repo's history). It turns `src/` into `docs/`, which GitHub Pages serves. The build fails on broken links or anchors, missing numbers, leftover placeholders and anything that looks personal.

- **Pages:** each page is `src/pages/<slug>/`, holding `_meta.json` and `NN-*.html` fragments, wrapped in `src/layout.html`.
- **Language:** English only for now (12 October 2026); the hidden `class="zh"` text is not kept up to date.
- **Numbers:** every number about an invention comes from `src/data/numbers_*.json`, with its source. The scripts in `tools/` regenerate those files from the simulation outputs.
- **Old links:** `src/redirects.json` maps old x-wow.com URLs to the new pages.
- **Logo:** `python tools/make_brand.py` (needs Pillow and NumPy) makes every logo size, the icons and the social preview from the two original files of the old site in `src/assets/img/brand/original/`. Nothing is redrawn: it only removes the white around the logo, keeps the white inside the ring (and fills the old favicon's see-through centre with white to match), and shows the ® mark light on dark backgrounds.

## Licences
- **Text, data and code:** [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
- **Hardware design files:** [CERN-OHL-P v2](https://ohwr.org/cern_ohl_p_v2.txt).
- **Slide images:** `src/assets/slides/` (and its built copy in `docs/`) holds SHRINK's 32 slide files (PMTiles, about 276 MB), CC0 1.0 by the owner's decision of 11 October 2026; its README says how they were made, and SHA256SUMS lists their checksums.
- **Exceptions:** the third-party code in `src/assets/vendor/` keeps its own licence: three.js (MIT), OpenSeadragon (BSD-3-Clause), PMTiles (BSD-3-Clause) and fflate inside it (MIT); see `src/assets/vendor/README.md`. The official licence texts (`LICENSE`, `tools/licenses/` and `LICENSES/` inside the SWELL zip) keep their publishers' own terms. Names and works credited on the site belong to their owners.
- **Name and logo:** X-WOW is a trade mark, and the X-WOW logo (which includes the name) is a registered UK trade mark, UK00003425680. The logo artwork is not covered by CC0 or CERN-OHL-P wherever it appears: `src/assets/img/brand/`, `src/favicon.ico`, `src/assets/img/og-xwow.png` and their built copies in `docs/`. CC0 never affects trade marks anyway (section 4a).
- **Patents:** see the legal notes on each invention page before any commercial use.

## AI transparency
This site's text and code, and the SWELL design, simulations and documents, were produced by an AI (Claude by Anthropic, used through Claude Code), working from the X-WOW owner's brief and orders. The archived projects are X-WOW's earlier work. Nothing here has been built or tested in a lab yet.
