from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
BUILD_STEPS = (
    "generate_national_pages.py",
    "create_buldang_highschool_math_page.py",
    "finalize_site.py",
    "generate_sitemap.py",
    "generate_rss.py",
)


def main() -> None:
    """Rebuild every generated page and finish the public discovery files.

    The one-off Buldang high-school math page must be recreated after the bulk
    generator because the bulk generator owns the nationwide directory tree.
    Keeping that order here prevents a later rebuild from silently removing it.
    """
    for script_name in BUILD_STEPS:
        script = TOOLS / script_name
        print(f"[build] {script_name}", flush=True)
        subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
