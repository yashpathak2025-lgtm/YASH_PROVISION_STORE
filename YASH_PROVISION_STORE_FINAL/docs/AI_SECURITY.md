# AI Security

## Architecture

User text/voice → OpenAI/Gemini provider adapter → structured JSON → schema validation → product resolution → backend permission check → preview → explicit confirmation → approved business service → database transaction.

The LLM is never given SQL execution tools, database credentials, or a generic query endpoint.

## Providers

Configure one provider through environment variables:

- `AI_PROVIDER=openai` + `OPENAI_API_KEY`
- `AI_PROVIDER=gemini` + `GEMINI_API_KEY`

Without a provider, the system uses only a deliberately limited controlled parser for simple stock/low-stock queries and explicitly reports that an LLM provider is not configured.

## Voice

`MediaRecorder` captures browser audio and `/api/voice/transcribe` sends it to the configured OpenAI transcription provider. The transcript is returned to the UI for editing. A destructive command is never executed directly from audio.

## Confirmation

Changing commands require Preview first. The preview includes action, product, old/new value, quantity/price, user and reason. Only `confirm=true` reaches the mutation branch.
