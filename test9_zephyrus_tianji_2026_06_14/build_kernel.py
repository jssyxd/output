"""Build a self-contained Kaggle kernel script.

Strategy: strip `from ... import` statements from inlined modules so everything
ends up in the single script's global namespace. Also disable `if __name__ == "__main__"`
blocks in non-main modules (they would auto-execute when inlined).
"""
import re
from pathlib import Path
project = Path("/home/da/桌面/Zephyrus")
out = Path("/tmp/shanghai_forecast_kernel.py")
parts = []
parts.append("# === Header: Zephyrus + TianJi forecast for Shanghai Pudong 2026-06-14 ===\n")
parts.append("# Bundled source: see open_meteo, consensus, reflective, main below.\n\n")

def strip_incompatible_imports(src: str) -> str:
    src = re.sub(r"^from __future__ import annotations\s*\n", "", src, flags=re.M)
    src = re.sub(r"^from src\.[\w\.]+ import \(.*?\)\s*\n", "", src, flags=re.S | re.M)
    src = re.sub(r"^from src\.[\w\.]+ import .*?\n", "", src, flags=re.M)
    src = re.sub(r"^from consensus import .*?\n", "", src, flags=re.M)
    src = re.sub(r"^from open_meteo import .*?\n", "", src, flags=re.M)
    return src

def disable_main_block(src: str, var_name: str = "__name__") -> str:
    # Replace `if __name__ == "__main__":` with `if False:` so it doesn't auto-run
    src = re.sub(rf'^if {var_name} == "__main__":\s*$',
                 f"if {var_name} != \"__main__\":  # disabled for Kaggle inlining",
                 src, flags=re.M)
    return src

parts.append("# === Inlined open_meteo.py ===\n")
om = (project / "src/zephyrus_world/open_meteo.py").read_text()
om = strip_incompatible_imports(om)
parts.append(om + "\n\n")

parts.append("# === Inlined consensus.py ===\n")
cs = (project / "src/agents/consensus.py").read_text()
cs = strip_incompatible_imports(cs)
cs = disable_main_block(cs)
parts.append(cs + "\n\n")

parts.append("# === Inlined reflective.py ===\n")
rf = (project / "src/agents/reflective.py").read_text()
rf = strip_incompatible_imports(rf)
rf = disable_main_block(rf)
parts.append(rf + "\n\n")

parts.append("# === Main entrypoint ===\n")
main_src = (project / "notebooks/shanghai_forecast.py").read_text()
main_src = strip_incompatible_imports(main_src)
parts.append(main_src)

out.write_text("\n".join(parts), encoding="utf-8")
print(f"Wrote {out.stat().st_size} bytes to {out}")
