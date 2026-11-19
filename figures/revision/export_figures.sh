#!/usr/bin/env bash
# Export figures/revision/Fig*.drawio to PDF with the draw.io desktop command
# line (tested with draw.io 32.6.10), then render the PNGs shown in README.md
# from those PDFs with Ghostscript.
#
#   DRAWIO=/path/to/drawio bash figures/revision/export_figures.sh
#
# The diagrams use the font Helvetica. On Linux without Helvetica, the script
# maps Helvetica (and Arial, sans-serif) to FreeSans, a TrueType Helvetica
# clone shipped with TeX Live, so that the PDFs embed TrueType fonts. On macOS
# and Windows, or when FreeSans is not found, the system fonts are used.
# Without a display, Electron needs --ozone-platform=headless (Linux only).
#
# Alternative without the command line: open the .drawio file in draw.io and
# use File > Export as > PDF with "Crop" ticked.
set -euo pipefail

figdir=$(cd "$(dirname "$0")" && pwd)
DRAWIO=${DRAWIO:-drawio}
flags=(-x -f pdf --crop)

if [[ $(uname -s) == Linux ]]; then
  flags=(--no-sandbox --disable-gpu --ozone-platform=headless "${flags[@]}")
  freesans=$(kpsewhich FreeSans.ttf 2>/dev/null || true)
  if [[ -n $freesans ]]; then
    conf=$(mktemp -d)/fonts.conf
    cat > "$conf" <<CONF
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <dir>$(dirname "$freesans")</dir>
  <dir>/usr/share/fonts</dir>
  <cachedir prefix="xdg">fontconfig-drawio-export</cachedir>
  <alias binding="same"><family>Helvetica</family><prefer><family>FreeSans</family></prefer></alias>
  <alias binding="same"><family>Arial</family><prefer><family>FreeSans</family></prefer></alias>
  <alias binding="same"><family>sans-serif</family><prefer><family>FreeSans</family></prefer></alias>
</fontconfig>
CONF
    export FONTCONFIG_FILE=$conf
  fi
fi

for src in "$figdir"/Fig*.drawio; do
  "$DRAWIO" "${flags[@]}" -o "${src%.drawio}.pdf" "$src"
  if command -v gs >/dev/null; then
    gs -q -dSAFER -dBATCH -dNOPAUSE -sDEVICE=png16m -r220 -dTextAlphaBits=4 \
       -dGraphicsAlphaBits=4 -o "${src%.drawio}.png" "${src%.drawio}.pdf"
  fi
done
