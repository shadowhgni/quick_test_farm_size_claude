# Preferences for Claude Code in this repository

## Branding (CIMMYT / CGIAR branding guidelines) - for figures, maps, reports, slides, web pages

Colours (hex, as given in the guidelines):

| Primary | | Secondary | |
|---|---|---|---|
| green | `#77bd42` | dark grey | `#54565b` |
| yellow | `#ffbf50` | pale olive | `#dddaa4` |
| brown | `#704b0f` | orange | `#f29657` |
| light blue | `#8ec1cb` | sage | `#acb7ac` |
| dark teal | `#326670` | taupe | `#b6a9a3` |

* Text and axes: dark grey `#54565b` (never a series colour for text). Grids: a light tint of it.
* Categorical series (checked with the dataviz palette validator, light background): use this order
  and keep it fixed - `#326670` teal, `#f29657` orange, `#704b0f` brown, `#77bd42` green. Colour-blind
  separation passes in this order (worst adjacent dE 23.9); **never put green `#77bd42` next to orange
  `#f29657`** (dE 3.6 for deuteranopia). Orange and green have < 3:1 contrast on white, so charts using
  them need direct labels or a legend + table. More than 4 series: facet or group into "other"
  (`#acb7ac` sage) rather than adding yellow / light blue (they read too light on white).
* Sequential maps: one-hue ramps built from a brand colour (e.g. light `#8ec1cb` -> dark `#326670` for
  "more of something", light `#ffbf50` -> `#704b0f` for dryness / risk). Diverging: `#326670` vs
  `#f29657` around a grey midpoint. Never rainbow ramps.
* Typography: Avenir (headings, body) and Circe Slab (accent headings). Both are commercial fonts and
  usually not installed - fall back to a similar sans-serif (e.g. "Avenir, 'Nunito Sans', 'DejaVu Sans',
  sans-serif") and say so; do not embed the fonts.
* Logos (CIMMYT / CGIAR, horizontal or square, colour / dark / white versions) only when the user
  supplies the logo files; never redraw or approximate them.

## Code (from the user's general preferences)

* Be explicit about the basis for claims (verified with a source / recalled / inferred); say "I don't
  know" rather than guess.
* R: native pipe `|>`, never `%>%`; tidyverse-first; only base R and the 8 core tidyverse packages are
  called bare, everything else as `package::function`.
