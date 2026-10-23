# Map boundaries

The home map's world and regional levels. Both files are cut by `tools/web/build_geo.mjs` from a one-off download, and they are not fetched at run time.

| File | Source | Licence |
|---|---|---|
| `world-50m.json` | [world-atlas](https://github.com/topojson/world-atlas) 2.0.2 `countries-50m.json`, copied as it is: Natural Earth 1:50m countries. | ISC (see `LICENSE-world-atlas`); Natural Earth data is public domain |
| `regions-10m.json` | [Natural Earth](https://www.naturalearthdata.com/) 1:10m admin-1 states and provinces, version 5 (`ne_10m_admin_1_states_provinces.geojson` from github.com/nvkelso/natural-earth-vector). Only Japan, Brazil, Australia, Chile, Peru, Ghana and Romania are kept, simplified to about 1 km with the borders kept shared. | Public domain |

The build script's comments explain three corrections. Macquarie Island is merged into Tasmania. Jervis Bay Territory is given the code `AU-JBT`. Metropolitan Lima is `PE-LMA`. Ghana is drawn with the ten regions Natural Earth has, not the sixteen it has had since 2018.

To rebuild, download the two source files and run:

    node tools/web/build_geo.mjs countries-50m.json ne_10m_admin_1_states_provinces.geojson dashboard/geo
