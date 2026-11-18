from pathlib import Path
from qopt.workload import generate

root = Path(__file__).resolve().parents[1]
pilot = generate(root, root / "workloads/job")
print("Selected:", ", ".join(r["query_id"] for r in pilot["queries"]))
