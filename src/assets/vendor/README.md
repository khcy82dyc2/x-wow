# Third-party code in this folder

None of it is X-WOW's, and none of it is covered by X-WOW's CC0 dedication: each part keeps its own licence, whose
full text sits beside it. The version comes from the code itself (three.js's `REVISION` constant).

| Folder | What | Version | Licence | Source |
|---|---|---|---|---|
| `three/` | three.js and OrbitControls (the SWELL concept model) | r160 (`REVISION`) | MIT (`three/LICENSE`) | https://github.com/mrdoob/three.js |
| `openseadragon/` | OpenSeadragon (the SHRINK viewer) | 4.1.1, built 2024-04-01 | BSD-3-Clause (`openseadragon/LICENSE.txt`) | https://openseadragon.github.io |
| `pmtiles/` | the PMTiles JavaScript reader (SHRINK's slide files) | 3.2.1, as SHRINK's bom.csv records (not read from the file itself) | BSD-3-Clause (`pmtiles/LICENSE`) | https://github.com/protomaps/PMTiles |
| `pmtiles/pmtiles.js` (bundled inside) | fflate (decompression) | not recorded | MIT (`pmtiles/LICENSE-fflate`: the upstream text, read 2026-10-10) | https://github.com/101arrowz/fflate |
