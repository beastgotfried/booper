# Model And Workspace Security

## Source Isolation

No tool writes to the supplied repository. Local inputs are copied and Git inputs are shallow
cloned into a run directory. Symlinks, VCS metadata, dependency trees, caches, and nested run output
are excluded. Model tools accept only exact eligible relative paths and reject absolute paths and
path traversal.

## Credentials

The Groq adapter reads `GROQ_API_KEY` or receives a key from the in-process SDK. The CLI does not
accept raw keys as arguments. Provider descriptors contain only provider name, model ID, and
capabilities. Reports, manifests, event streams, prompts, and errors never intentionally include a
key, and common provider-key patterns are redacted from captured errors.

## Data Egress

Deterministic runs make no model calls. In agent or hybrid mode, repository metadata, file paths,
bounded source returned by `read_source`, and bounded diffs can be sent to the selected provider.
Users must treat this as source-code disclosure to that provider and should not enable a hosted
model for repositories whose policy prohibits it.

## Prompt Injection

The system prompt treats repository text as untrusted data. Source cannot change the available tool
schemas, candidate path map, mutation allowlist, mutation budget, or write validation. A model can
request only the five session-bound tools, and each tool independently validates its inputs.

## Rewrite Validation

Whole-file model rewrites are optional. They are rejected when they exceed the configured size,
contain Markdown fences, target an ineligible file, exceed budget, or fail Python parsing. This
protects harness integrity; it does not prove semantic equivalence. Runs remain isolated and emit a
complete patch so a human can inspect the result before using it elsewhere.
