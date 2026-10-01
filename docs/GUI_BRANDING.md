# GUI branding / logo detection

Stockless ships a machine-readable `engine-branding.json` plus `assets/stockless-logo.svg`.

## Detection

After the normal UCI handshake, a GUI should use the engine's `id name`. If it starts with `Stockless` (case-insensitive), display `assets/stockless-logo.svg`.

For packaged engines, the GUI may instead read `engine-branding.json` and resolve the logo path relative to the manifest.

> UCI does not define a standard command for transferring an engine logo. The manifest is therefore the portable Stockless convention; existing third-party GUIs need explicit support for it.

Suggested lookup order:

1. `engine-branding.json`
2. UCI `id name Stockless...`
3. executable filename `stockless*`

Keep the SVG alongside distributed binaries so desktop and Android GUIs can render the same branding.
