# Switching LLM Models in Skyflo

This guide explains how to configure Skyflo to use different LLM providers and models using environment variables in the `engine/.env` file.

## Configuration Steps

Configuring the LLM involves setting API keys and selecting the active model in your `engine/.env` file.

### 1. Set API Keys

Add API keys for each provider you might use, following the pattern `{PROVIDER_NAME}_API_KEY`:

```env
# Required if using OpenAI models
OPENAI_API_KEY=sk-...

# Required if using Groq models
GROQ_API_KEY=gsk-...

# Required if using Anthropic models
ANTHROPIC_API_KEY=sk-ant-...

# Add keys for other providers as needed (COHERE_API_KEY, AZURE_API_KEY, etc.)
```

### 2. Set Active Model (`OPENAI_MODEL`)

Use the `OPENAI_MODEL` variable to specify the _single_ model Skyflo should use. Only one `OPENAI_MODEL` line should be active (uncommented). Any LLM should be added under the `OPENAI_MODEL` key only.

**Naming Convention:**

- **OpenAI Models**: Use only the model name (e.g., `gpt-4o`). **Do not** include the `openai/` prefix.
- **Other Providers**: **Must** include the `provider/` prefix (e.g., `groq/llama-3-70b-versatile`, `anthropic/claude-3-sonnet`).

```env
# Example: Activate OpenAI's GPT-4o
OPENAI_MODEL=gpt-4o

# Example: Activate Groq's Llama 3 (ensure the line above is commented out)
# OPENAI_MODEL=groq/llama-3-70b-versatile
```

> **Note:** Despite the variable name `OPENAI_MODEL`, it controls model selection for _all_ providers.

### 3. How it Works (Automatic Key Selection)

Skyflo automatically uses the correct API key based on your `OPENAI_MODEL` setting:

1.  It reads the `OPENAI_MODEL` value (e.g., `groq/llama-3-70b-versatile`).
2.  It extracts the provider (`groq`). If no `/` is found, it defaults to `openai`.
3.  It looks for and uses the corresponding API key variable (`GROQ_API_KEY` or `OPENAI_API_KEY`).

This allows easy switching just by changing the `OPENAI_MODEL` value and restarting the application.

### 4. Restart Application

After modifying the `.env` file, restart the Skyflo application components (e.g., the API service pod) for changes to take effect.

## Model Capability Requirements

Skyflo requires LLMs that can generate structured JSON output for planning and analysis.

1.  **Mandatory: `response_format` Support**: The model **must** support requesting JSON output (e.g., `{"type": "json_object"}`). Most modern models do. Lack of this capability will cause errors.
2.  **Recommended: `json_schema` Support**: Explicit support for detailed JSON schema enforcement (`{"type": "json_schema", ...}`) is **highly recommended** for reliability, especially with complex internal operations. Models supporting only basic JSON _might_ work but could produce invalid structures.

**Recommendation**: Verify model capabilities (especially JSON output support) in the provider's documentation or [LiteLLM's provider list](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json) before configuring. Prioritize models with explicit JSON schema support for the most reliable operation with Skyflo.

## Supported Providers

Skyflo supports providers available through LiteLLM, including OpenAI, Groq, Anthropic, Cohere, Azure, Ollama, and many others. See the [LiteLLM documentation](https://litellm.vercel.app/docs/providers) for details.

## Troubleshooting

- **API Key Errors**: Ensure the correct `{PROVIDER}_API_KEY` variable exists and the key value is valid in `.env`.
- **Model Not Found Errors**: Double-check `OPENAI_MODEL` presence. Ensure correct prefix usage (present for non-OpenAI, absent for OpenAI). Verify model access/support with the provider.
- **Rate Limiting**: Provider-specific issue; consult their documentation.
- **Changes Not Taking Effect**: Ensure the Skyflo application was restarted after saving `.env` changes.
