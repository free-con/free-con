#!/usr/bin/env python3
"""Jarvis'i başlatır.

    python jarvis.py              # sesli mod ("Jarvis ..." diye seslenin)
    python jarvis.py --yazi       # klavyeden yazarak
    python jarvis.py --yazi --konus   # yazarak sorun, sesli cevap alın
    python jarvis.py --ses-testi  # hoparlör ve mikrofon testi
"""

import sys

if sys.version_info < (3, 10):
    sys.exit("Jarvis için Python 3.10 veya daha yeni bir sürüm gerekiyor.")

from jarvis_core.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
