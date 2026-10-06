# Sequential Matching Data Viewer

This is a plain, local, dependency-free viewer for inspecting the public
synthetic dataset, current policy output and saved evaluation results. The
interface is policy-independent: changing the algorithm does not require a new
visual design.

## Build the observable dashboard data

From the repository root:

```powershell
python frontend/build_dashboard_data.py
```

The generated `frontend/data/dashboard.json` is ignored by Git because it is a
local derivative of the committed public snapshots and experiment files.

## Open the dashboard

```powershell
python -m http.server 8080 --directory frontend
```

Then open `http://localhost:8080`.

## Evidence boundary

The data builder exports only observable public snapshot fields and trusted local
evaluation results. It does not export simulator truth, hidden preferences,
generator seeds or private organiser data.

The interface labels all results as synthetic preliminary evidence. It is a
research and debugging tool, not a real-member product interface.
