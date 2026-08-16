# CLI

The CLI is installed from the root package as `enshittify`. It is intentionally thin: repository
staging comes from `enshittify_backends`, orchestration comes from `enshittify_core`, and the public
entry path comes from `enshittify_sdk`.

Provider-backed runs read keys from environment variables and use `enshittify_providers`; the CLI
never owns model clients or mutation logic.

Run `enshittify --help` for usage.
