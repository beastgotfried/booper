# Python SDK Reference

`Enshittify` runs the harness in process without the CLI or app server.

```python
from enshittify_sdk import Enshittify

client = Enshittify(output_root="./enshittify-runs")
result = client.run_repository(
    source="./repository",
    profile="enterprise-sprawl",
    intensity="high",
    budget=100,
    output="workspace",
)
```

The returned result exposes `run_id`, `status`, `run_dir`, `workspace_dir`, `report_path`,
`patch_path`, `archive_path`, `changed_files`, and the complete `report` dictionary.
