# Vendored vehicle data

`dtc-td5.json` and `dtc-slabs.json` are the fault-code meanings (key, name, likely cause)
from the Ostler Discovery 2 pack, `src/d2diag/dtc/*.json` at commit
`f9b2af2f62471a96acd9589d7a3b5fb966ba17fd` (https://github.com/openostler/ostler-pack-lr-d2),
reduced to the fields the dashboard shows.

They are licensed CC BY-SA 4.0 by the Ostler project (see that repository's `LICENSE-DATA`),
separately from this repository's AGPL-3.0 code. When `d2diag` is installed, its own copy is
used in preference to these, so a newer dictionary upstream shows up after a reinstall.
