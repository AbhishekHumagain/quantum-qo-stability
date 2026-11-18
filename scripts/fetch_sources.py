"""Fetch exact upstream revisions; never reset or overwrite existing checkouts."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
sources = {
    "pg_hint_plan": ("https://github.com/ossc-db/pg_hint_plan.git", "9a3f851e1993d6728a9707956dabfcf22cc35b38"),
    "qdbo": ("https://github.com/ihanwen99/VLDB26-QDBO.git", "2c8a3b3429634eb5d810b98f343b8729555c24b1"),
    "q2o": ("https://github.com/ihanwen99/Q2O.git", "1b4b1cd2f1f698cce85c5cb9b94286c681555711"),
    "job": ("https://github.com/gregrahn/join-order-benchmark.git", "a39603662e023e449cb2121997a5034df9e02ebf"),
}
for name, (url, revision) in sources.items():
    target = root / "vendor" / name
    if not target.exists():
        target.mkdir(parents=True)
        subprocess.run(["git", "init", str(target)], check=True)
        subprocess.run(["git", "-C", str(target), "remote", "add", "origin", url], check=True)
        subprocess.run(["git", "-C", str(target), "fetch", "--depth", "1", "origin", revision], check=True)
        subprocess.run(["git", "-C", str(target), "checkout", "--detach", "FETCH_HEAD"], check=True)
    actual = subprocess.check_output(["git", "-C", str(target), "rev-parse", "HEAD"], text=True).strip()
    if actual != revision:
        raise SystemExit(f"{name}: expected {revision}, found {actual}; checkout left untouched")
    print(f"{name}: {actual}")
