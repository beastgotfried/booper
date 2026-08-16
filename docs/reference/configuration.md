# Configuration

## Environment

- `GROQ_API_KEY`: GroqCloud API key used when `provider="groq"`.
- `ENSHITTIFY_CODX_COMMAND`: optional executable or absolute path for the local Codx wrapper.
- `ENSHITTIFY_CODX_MODEL`: optional model label recorded for Codx runs.
- `ENSHITTIFY_CODX_TIMEOUT`: convenience variable for the live smoke script; SDK callers pass
  `codx_timeout` directly.

## Provider Defaults

- Provider: `none`
- Groq model: `openai/gpt-oss-120b`
- Codx command: `codx`
- Codx model label: `codex-default`
- Codx process timeout: `1800` seconds
- Mode: `auto`
- Temperature: `0`
- Request timeout: `120` seconds
- Provider retries: `2`
- Completion limit: `8192` tokens
- Agent steps: `24`
- Source returned per read: `24000` characters

The default model is kept in the provider adapter and shown by `enshittify providers --json` so it
can be updated independently from the core harness.
