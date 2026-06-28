#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# WebKitGTK on some KDE/Wayland/NVIDIA setups can open a blank window when
# DMA-BUF/GBM accelerated rendering fails. Prefer the safer X11/WebKit path for
# the beta release package.
export GDK_BACKEND="${GDK_BACKEND:-x11}"
export WEBKIT_DISABLE_DMABUF_RENDERER="${WEBKIT_DISABLE_DMABUF_RENDERER:-1}"
export WEBKIT_DISABLE_COMPOSITING_MODE="${WEBKIT_DISABLE_COMPOSITING_MODE:-1}"

if [ "${1:-}" = "--software" ]; then
  export LIBGL_ALWAYS_SOFTWARE=1
  shift
fi

exec ./omnibet-lab "$@"
