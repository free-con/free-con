#!/usr/bin/env bash
# Mac'te çift tıklanabilir başlatıcı. Asıl işi tasinabilir-mac-linux.sh yapar.
cd "$(dirname "$0")" || exit 1
exec bash ./tasinabilir-mac-linux.sh "$@"
