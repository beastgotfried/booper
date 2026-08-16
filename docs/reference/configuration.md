# Configuration

## Environment

- `GROQ_API_KEY`: GroqCloud API key used when `provider="groq"`.

## Provider Defaults

- Provider: `none`
- Groq model: `openai/gpt-oss-120b`
- Mode: `auto`
- Temperature: `0`
- Request timeout: `120` seconds
- Provider retries: `2`
- Completion limit: `8192` tokens
- Agent steps: `24`
- Source returned per read: `24000` characters

The default model is kept in the provider adapter and shown by `enshittify providers --json` so it
can be updated independently from the core harness.
