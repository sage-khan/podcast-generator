---
title: OpenRouter Integration
subtitle: Using OpenRouter API in this project
headline: OpenRouter API Integration | Podcast Generator
---

# OpenRouter Integration

This documentation explains how OpenRouter API is integrated within this AI media generation platform, particularly for podcast script generation using Gemini models.

## How OpenRouter is Used in This Project

In this platform, OpenRouter provides access to Gemini AI models used primarily for:

1. Podcast script generation in the podcast_generator module
2. Image analysis for speaker characteristics
3. Background prompt generation for consistent visual themes

## Environment Configuration

OpenRouter API access requires an API key configured in your environment:

```
OPENROUTER_API_KEY=your_api_key_here
```

This key is referenced in Django settings and used by the podcast generation services.

## Accessing OpenRouter Endpoints via Swagger UI

With the Swagger UI integration, you can now explore and test the OpenRouter-powered endpoints directly:

1. Access the Swagger UI at: `/api/docs/`
2. Navigate to the Podcast Generation section
3. Authenticate using the "Authorize" button
4. Test the script generation endpoints that use OpenRouter's Gemini models

## Additional Documentation

For more details on the OpenRouter API itself, refer to the following sections:

---
title: Authentication
subtitle: API Authentication
headline: API Authentication | OpenRouter OAuth and API Keys
canonical-url: 'https://openrouter.ai/docs/api-reference/authentication'
'og:site_name': OpenRouter Documentation
'og:title': API Authentication - Secure Access to OpenRouter
'og:description': >-
  Learn how to authenticate with OpenRouter using API keys and Bearer tokens.
  Complete guide to secure authentication methods and best practices.
'og:image':
  type: url
  value: >-
    https://openrouter.ai/dynamic-og?title=API%20Authentication&description=Secure%20access%20to%20OpenRouter
'og:image:width': 1200
'og:image:height': 630
'twitter:card': summary_large_image
'twitter:site': '@OpenRouterAI'
noindex: false
nofollow: false
---

You can cover model costs with OpenRouter API keys.

Our API authenticates requests using Bearer tokens. This allows you to use `curl` or the [OpenAI SDK](https://platform.openai.com/docs/frameworks) directly with OpenRouter.

<Warning>
API keys on OpenRouter are more powerful than keys used directly for model APIs.

They allow users to set credit limits for apps, and they can be used in [OAuth](/docs/use-cases/oauth-pkce) flows.

</Warning>

## Using an API key

To use an API key, [first create your key](https://openrouter.ai/keys). Give it a name and you can optionally set a credit limit.

If you're calling the OpenRouter API directly, set the `Authorization` header to a Bearer token with your API key.

If you're using the OpenAI Typescript SDK, set the `api_base` to `https://openrouter.ai/api/v1` and the `apiKey` to your API key.

<CodeGroup>

```typescript title="TypeScript (Bearer Token)"
fetch('https://openrouter.ai/api/v1/chat/completions', {
  method: 'POST',
  headers: {
    Authorization: 'Bearer <OPENROUTER_API_KEY>',
    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.
    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: 'openai/gpt-4o',
    messages: [
      {
        role: 'user',
        content: 'What is the meaning of life?',
      },
    ],
  }),
});
```

```typescript title="TypeScript (OpenAI SDK)"
import OpenAI from 'openai';

const openai = new OpenAI({
  baseURL: 'https://openrouter.ai/api/v1',
  apiKey: '<OPENROUTER_API_KEY>',
  defaultHeaders: {
    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.
    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.
  },
});

async function main() {
  const completion = await openai.chat.completions.create({
    model: 'openai/gpt-4o',
    messages: [{ role: 'user', content: 'Say this is a test' }],
  });

  console.log(completion.choices[0].message);
}

main();
```

```python title="Python"
import openai

openai.api_base = "https://openrouter.ai/api/v1"
openai.api_key = "<OPENROUTER_API_KEY>"

response = openai.ChatCompletion.create(
  model="openai/gpt-4o",
  messages=[...],
  headers={
    "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
    "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
  },
)

reply = response.choices[0].message
```

```shell title="Shell"
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -d '{
  "model": "openai/gpt-4o",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ]
}'
```

</CodeGroup>

To stream with Python, [see this example from OpenAI](https://github.com/openai/openai-cookbook/blob/main/examples/How_to_stream_completions.ipynb).

## If your key has been exposed

<Warning>
  You must protect your API keys and never commit them to public repositories.
</Warning>

OpenRouter is a GitHub secret scanning partner, and has other methods to detect exposed keys. If we determine that your key has been compromised, you will receive an email notification.

If you receive such a notification or suspect your key has been exposed, immediately visit [your key settings page](https://openrouter.ai/settings/keys) to delete the compromised key and create a new one.

Using environment variables and keeping keys out of your codebase is strongly recommended.


---
title: Model Routing
subtitle: Dynamically route requests to models
headline: Model Routing | Dynamic AI Model Selection and Fallback
canonical-url: 'https://openrouter.ai/docs/features/model-routing'
'og:site_name': OpenRouter Documentation
'og:title': Model Routing - Smart Model Selection and Fallback
'og:description': >-
  Route requests dynamically between AI models. Learn how to use OpenRouter's
  Auto Router and model fallback features for optimal performance and
  reliability.
'og:image':
  type: url
  value: >-
    https://openrouter.ai/dynamic-og?title=Model%20Routing&description=Dynamic%20AI%20model%20selection%20and%20fallbacks
'og:image:width': 1200
'og:image:height': 630
'twitter:card': summary_large_image
'twitter:site': '@OpenRouterAI'
noindex: false
nofollow: false
---

import { API_KEY_REF } from '../../../imports/constants';

OpenRouter provides two options for model routing.

## Auto Router

The [Auto Router](https://openrouter.ai/openrouter/auto), a special model ID that you can use to choose between selected high-quality models based on your prompt, powered by [NotDiamond](https://www.notdiamond.ai/).

```json
{
  "model": "openrouter/auto",
  ... // Other params
}
```

The resulting generation will have `model` set to the model that was used.

## The `models` parameter

The `models` parameter lets you automatically try other models if the primary model's providers are down, rate-limited, or refuse to reply due to content moderation.

```json
{
  "models": ["anthropic/claude-3.5-sonnet", "gryphe/mythomax-l2-13b"],
  ... // Other params
}
```

If the model you selected returns an error, OpenRouter will try to use the fallback model instead. If the fallback model is down or returns an error, OpenRouter will return that error.

By default, any error can trigger the use of a fallback model, including context length validation errors, moderation flags for filtered models, rate-limiting, and downtime.

Requests are priced using the model that was ultimately used, which will be returned in the `model` attribute of the response body.

## Using with OpenAI SDK

To use the `models` array with the OpenAI SDK, include it in the `extra_body` parameter. In the example below, gpt-4o will be tried first, and the `models` array will be tried in order as fallbacks.

<Template data={{
  API_KEY_REF,
}}>
<CodeGroup>

```typescript
import OpenAI from 'openai';

const openrouterClient = new OpenAI({
  baseURL: 'https://openrouter.ai/api/v1',
  // API key and headers
});

async function main() {
  // @ts-expect-error
  const completion = await openrouterClient.chat.completions.create({
    model: 'openai/gpt-4o',
    models: ['anthropic/claude-3.5-sonnet', 'gryphe/mythomax-l2-13b'],
    messages: [
      {
        role: 'user',
        content: 'What is the meaning of life?',
      },
    ],
  });
  console.log(completion.choices[0].message);
}

main();
```

```python
from openai import OpenAI

openai_client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key={{API_KEY_REF}},
)

completion = openai_client.chat.completions.create(
    model="openai/gpt-4o",
    extra_body={
        "models": ["anthropic/claude-3.5-sonnet", "gryphe/mythomax-l2-13b"],
    },
    messages=[
        {
            "role": "user",
            "content": "What is the meaning of life?"
        }
    ]
)

print(completion.choices[0].message.content)
```

</CodeGroup>
</Template>


---
title: Provider Routing
subtitle: Route requests to the best provider
headline: Provider Routing | Intelligent Multi-Provider Request Routing
canonical-url: 'https://openrouter.ai/docs/features/provider-routing'
'og:site_name': OpenRouter Documentation
'og:title': Provider Routing - Smart Multi-Provider Request Management
'og:description': >-
  Route AI model requests across multiple providers intelligently. Learn how to
  optimize for cost, performance, and reliability with OpenRouter's provider
  routing.
'og:image':
  type: url
  value: >-
    https://openrouter.ai/dynamic-og?pathname=features/provider-routing&title=Smart%20Routing&description=Optimize%20AI%20requests%20across%20providers%20for%20best%20performance
'og:image:width': 1200
'og:image:height': 630
'twitter:card': summary_large_image
'twitter:site': '@OpenRouterAI'
noindex: false
nofollow: false
---
import { ProviderPreferencesSchema } from '../../../imports/constants';
import { TSFetchCodeBlock } from '../../../imports/TSFetchCodeBlock';
import { ZodToJSONSchemaBlock } from '../../../imports/ZodToJSONSchemaBlock';
import { TermsOfServiceDescriptions } from '../../../imports/TermsOfServiceDescriptions';

OpenRouter routes requests to the best available providers for your model. By default, [requests are load balanced](#load-balancing-default-strategy) across the top providers to maximize uptime.

You can customize how your requests are routed using the `provider` object in the request body for [Chat Completions](/docs/api-reference/chat-completion) and [Completions](/docs/api-reference/completion).

<Tip>
  For a complete list of valid provider names to use in the API, see the [full
  provider schema](#json-schema-for-provider-preferences).
</Tip>

The `provider` object can contain the following fields:

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `order` | string[] | - | List of provider slugs to try in order (e.g. `["anthropic", "openai"]`). [Learn more](#ordering-specific-providers) |
| `allow_fallbacks` | boolean | `true` | Whether to allow backup providers when the primary is unavailable. [Learn more](#disabling-fallbacks) |
| `require_parameters` | boolean | `false` | Only use providers that support all parameters in your request. [Learn more](#requiring-providers-to-support-all-parameters-beta) |
| `data_collection` | "allow" \| "deny" | "allow" | Control whether to use providers that may store data. [Learn more](#requiring-providers-to-comply-with-data-policies) |
| `only` | string[] | - | List of provider slugs to allow for this request. [Learn more](#allowing-only-specific-providers) |
| `ignore` | string[] | - | List of provider slugs to skip for this request. [Learn more](#ignoring-providers) |
| `quantizations` | string[] | - | List of quantization levels to filter by (e.g. `["int4", "int8"]`). [Learn more](#quantization) |
| `sort` | string | - | Sort providers by price or throughput. (e.g. `"price"` or `"throughput"`). [Learn more](#provider-sorting) |
| `max_price` | object | - | The maximum pricing you want to pay for this request. [Learn more](#maximum-price) |

## Price-Based Load Balancing (Default Strategy)

For each model in your request, OpenRouter's default behavior is to load balance requests across providers, prioritizing price.

If you are more sensitive to throughput than price, you can use the `sort` field to explicitly prioritize throughput.

<Tip>
  When you send a request with `tools` or `tool_choice`, OpenRouter will only
  route to providers that support tool use. Similarly, if you set a
  `max_tokens`, then OpenRouter will only route to providers that support a
  response of that length.
</Tip>

Here is OpenRouter's default load balancing strategy:

1. Prioritize providers that have not seen significant outages in the last 30 seconds.
2. For the stable providers, look at the lowest-cost candidates and select one weighted by inverse square of the price (example below).
3. Use the remaining providers as fallbacks.

<Note title="A Load Balancing Example">
If Provider A costs \$1 per million tokens, Provider B costs \$2, and Provider C costs \$3, and Provider B recently saw a few outages.

- Your request is routed to Provider A. Provider A is 9x more likely to be first routed to Provider A than Provider C because $(1 / 3^2 = 1/9)$ (inverse square of the price).
- If Provider A fails, then Provider C will be tried next.
- If Provider C also fails, Provider B will be tried last.

</Note>

If you have `sort` or `order` set in your provider preferences, load balancing will be disabled.

## Provider Sorting

As described above, OpenRouter load balances based on price, while taking uptime into account.

If you instead want to _explicitly_ prioritize a particular provider attribute, you can include the `sort` field in the `provider` preferences. Load balancing will be disabled, and the router will try providers in order.

The three sort options are:

- `"price"`: prioritize lowest price
- `"throughput"`: prioritize highest throughput
- `"latency"`: prioritize lowest latency

<TSFetchCodeBlock
  title='Example with Fallbacks Enabled'
  uriPath='/api/v1/chat/completions'
  body={{
    model: 'meta-llama/llama-3.1-70b-instruct',
    messages: [{ role: 'user', content: 'Hello' }],
    provider: {
      sort: 'throughput',
    },
  }}
/>

To _always_ prioritize low prices, and not apply any load balancing, set `sort` to `"price"`.

To _always_ prioritize low latency, and not apply any load balancing, set `sort` to `"latency"`.

## Nitro Shortcut

You can append `:nitro` to any model slug as a shortcut to sort by throughput. This is exactly equivalent to setting `provider.sort` to `"throughput"`.

<TSFetchCodeBlock
  title='Example using Nitro shortcut'
  uriPath='/api/v1/chat/completions'
  body={{
    model: 'meta-llama/llama-3.1-70b-instruct:nitro',
    messages: [{ role: 'user', content: 'Hello' }],
  }}
/>

## Floor Price Shortcut

You can append `:floor` to any model slug as a shortcut to sort by price. This is exactly equivalent to setting `provider.sort` to `"price"`.

<TSFetchCodeBlock
  title='Example using Floor shortcut'
  uriPath='/api/v1/chat/completions'
  body={{
    model: 'meta-llama/llama-3.1-70b-instruct:floor',
    messages: [{ role: 'user', content: 'Hello' }],
  }}
/>

## Ordering Specific Providers

You can set the providers that OpenRouter will prioritize for your request using the `order` field.

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `order` | string[] | - | List of provider slugs to try in order (e.g. `["anthropic", "openai"]`). |

The router will prioritize providers in this list, and in this order, for the model you're using. If you don't set this field, the router will [load balance](#load-balancing-default-strategy) across the top providers to maximize uptime.

<Tip>
  You can use the copy button next to provider names on model pages to get the exact provider slug, 
  including any variants like "/turbo". See [Targeting Specific Provider Endpoints](#targeting-specific-provider-endpoints) for details.
</Tip>

OpenRouter will try them one at a time and proceed to other providers if none are operational. If you don't want to allow any other providers, you should [disable fallbacks](#disabling-fallbacks) as well.

### Example: Specifying providers with fallbacks

This example skips over OpenAI (which doesn't host Mixtral), tries Together, and then falls back to the normal list of providers on OpenRouter:

<TSFetchCodeBlock
  title='Example with Fallbacks Enabled'
  uriPath='/api/v1/chat/completions'
  body={{
    model: 'mistralai/mixtral-8x7b-instruct',
    messages: [{ role: 'user', content: 'Hello' }],
    provider: {
      order: ['openai', 'together'],
    },
  }}
/>

### Example: Specifying providers with fallbacks disabled

Here's an example with `allow_fallbacks` set to `false` that skips over OpenAI (which doesn't host Mixtral), tries Together, and then fails if Together fails:

<TSFetchCodeBlock
  title='Example with Fallbacks Disabled'
  uriPath='/api/v1/chat/completions'
  body={{
    model: 'mistralai/mixtral-8x7b-instruct',
    messages: [{ role: 'user', content: 'Hello' }],
    provider: {
      order: ['openai', 'together'],
      allow_fallbacks: false,
    },
  }}
/>

## Targeting Specific Provider Endpoints

Each provider on OpenRouter may host multiple endpoints for the same model, such as a default endpoint and a specialized "turbo" endpoint. To target a specific endpoint, you can use the copy button next to the provider name on the model detail page to obtain the exact provider slug.

For example, DeepInfra offers DeepSeek R1 through multiple endpoints:
- Default endpoint with slug `deepinfra`
- Turbo endpoint with slug `deepinfra/turbo`

By copying the exact provider slug and using it in your request's `order` array, you can ensure your request is routed to the specific endpoint you want:

<TSFetchCodeBlock
  title='Example targeting DeepInfra Turbo endpoint'
  uriPath='/api/v1/chat/completions'
  body={{
    model: 'deepseek/deepseek-r1',
    messages: [{ role: 'user', content: 'Hello' }],
    provider: {
      order: ['deepinfra/turbo'],
      allow_fallbacks: false,
    },
  }}
/>

This approach is especially useful when you want to consistently use a specific variant of a model from a particular provider.

## Requiring Providers to Support All Parameters

You can restrict requests only to providers that support all parameters in your request using the `require_parameters` field.

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `require_parameters` | boolean | `false` | Only use providers that support all parameters in your request. |

With the default routing strategy, providers that don't support all the [LLM parameters](/docs/api-reference/parameters) specified in your request can still receive the request, but will ignore unknown parameters. When you set `require_parameters` to `true`, the request won't even be routed to that provider.

### Example: Excluding providers that don't support JSON formatting

For example, to only use providers that support JSON formatting:

<TSFetchCodeBlock
  uriPath='/api/v1/chat/completions'
  body={{
    messages: [{ role: 'user', content: 'Hello' }],
    provider: {
      require_parameters: true,
    },
    response_format: { type: 'json_object' },
  }}
/>

## Requiring Providers to Comply with Data Policies

You can restrict requests only to providers that comply with your data policies using the `data_collection` field.

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `data_collection` | "allow" \| "deny" | "allow" | Control whether to use providers that may store data. |

- `allow`: (default) allow providers which store user data non-transiently and may train on it
- `deny`: use only providers which do not collect user data

Some model providers may log prompts, so we display them with a **Data Policy** tag on model pages. This is not a definitive source of third party data policies, but represents our best knowledge.

<Tip title='Account-Wide Data Policy Filtering'>
  This is also available as an account-wide setting in [your privacy
  settings](https://openrouter.ai/settings/privacy). You can disable third party
  model providers that store inputs for training.
</Tip>

### Example: Excluding providers that don't comply with data policies

To exclude providers that don't comply with your data policies, set `data_collection` to `deny`:

<TSFetchCodeBlock
  uriPath='/api/v1/chat/completions'
  body={{
    messages: [{ role: 'user', content: 'Hello' }],
    provider: {
      data_collection: 'deny', // or "allow"
    },
  }}
/>

## Disabling Fallbacks

To guarantee that your request is only served by the top (lowest-cost) provider, you can disable fallbacks.

This is combined with the `order` field from [Ordering Specific Providers](#ordering-specific-providers) to restrict the providers that OpenRouter will prioritize to just your chosen list.

<TSFetchCodeBlock
  uriPath='/api/v1/chat/completions'
  body={{
    messages: [{ role: 'user', content: 'Hello' }],
    provider: {
      allow_fallbacks: false,
    },
  }}
/>

## Allowing Only Specific Providers

You can allow only specific providers for a request by setting the `only` field in the `provider` object.

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `only` | string[] | - | List of provider slugs to allow for this request. |

<Warning>
    Only allowing some providers may significantly reduce fallback options and
    limit request recovery.
</Warning>

<Tip title="Account-Wide Allowed Providers">
    You can allow providers for all account requests by configuring your [preferences](/settings/preferences). This configuration applies to all API requests and chatroom messages.

    Note that when you allow providers for a specific request, the list of allowed providers is merged with your account-wide allowed providers.

</Tip>


### Example: Allowing Azure for a request calling GPT-4 Omni

Here's an example that will only use Azure for a request calling GPT-4 Omni:

<TSFetchCodeBlock
    uriPath='/api/v1/chat/completions'
    body={{
        model: 'openai/gpt-4o',
        messages: [{ role: 'user', content: 'Hello' }],
        provider: {
            only: ['azure'],
        },
    }}
/>

## Ignoring Providers

You can ignore providers for a request by setting the `ignore` field in the `provider` object.

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `ignore` | string[] | - | List of provider slugs to skip for this request. |

<Warning>
  Ignoring multiple providers may significantly reduce fallback options and
  limit request recovery.
</Warning>

<Tip title="Account-Wide Ignored Providers">
You can ignore providers for all account requests by configuring your [preferences](/settings/preferences). This configuration applies to all API requests and chatroom messages.

Note that when you ignore providers for a specific request, the list of ignored providers is merged with your account-wide ignored providers.

</Tip>

### Example: Ignoring DeepInfra for a request calling Llama 3.3 70b

Here's an example that will ignore DeepInfra for a request calling Llama 3.3 70b:

<TSFetchCodeBlock
  uriPath='/api/v1/chat/completions'
  body={{
    model: 'meta-llama/llama-3.3-70b-instruct',
    messages: [{ role: 'user', content: 'Hello' }],
    provider: {
      ignore: ['deepinfra'],
    },
  }}
/>

## Quantization

Quantization reduces model size and computational requirements while aiming to preserve performance. Most LLMs today use FP16 or BF16 for training and inference, cutting memory requirements in half compared to FP32. Some optimizations use FP8 or quantization to reduce size further (e.g., INT8, INT4).

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `quantizations` | string[] | - | List of quantization levels to filter by (e.g. `["int4", "int8"]`). [Learn more](#quantization) |

<Warning>
  Quantized models may exhibit degraded performance for certain prompts,
  depending on the method used.
</Warning>

Providers can support various quantization levels for open-weight models.

### Quantization Levels

By default, requests are load-balanced across all available providers, ordered by price. To filter providers by quantization level, specify the `quantizations` field in the `provider` parameter with the following values:

- `int4`: Integer (4 bit)
- `int8`: Integer (8 bit)
- `fp4`: Floating point (4 bit)
- `fp6`: Floating point (6 bit)
- `fp8`: Floating point (8 bit)
- `fp16`: Floating point (16 bit)
- `bf16`: Brain floating point (16 bit)
- `fp32`: Floating point (32 bit)
- `unknown`: Unknown

### Example: Requesting FP8 Quantization

Here's an example that will only use providers that support FP8 quantization:

<TSFetchCodeBlock
  uriPath='/api/v1/chat/completions'
  body={{
    model: 'meta-llama/llama-3.1-8b-instruct',
    messages: [{ role: 'user', content: 'Hello' }],
    provider: {
      quantizations: ['fp8'],
    },
  }}
/>

### Max Price

To filter providers by price, specify the `max_price` field in the `provider` parameter with a JSON object specifying the highest provider pricing you will accept.

For example, the value `{"prompt": 1, "completion": 2}` will route to any provider with a price of `<= $1/m` prompt tokens, and `<= $2/m` completion tokens or less.

Some providers support per request pricing, in which case you can use the `request` attribute of max_price. Lastly, `image` is also available, which specifies the max price per image you will accept.

Practically, this field is often combined with a provider `sort` to express, for example, "Use the provider with the highest throughput, as long as it doesn\'t cost more than `$x/m` tokens."


## Terms of Service

You can view the terms of service for each provider below. You may not violate the terms of service or policies of third-party providers that power the models on OpenRouter.

<TermsOfServiceDescriptions />

## JSON Schema for Provider Preferences

For a complete list of options, see this JSON schema:

<ZodToJSONSchemaBlock
  title='Provider Preferences Schema'
  schema={ProviderPreferencesSchema}
/>


---
title: Structured Outputs
subtitle: Return structured data from your models
headline: Structured Outputs | Enforce JSON Schema in OpenRouter API Responses
canonical-url: 'https://openrouter.ai/docs/features/structured-outputs'
'og:site_name': OpenRouter Documentation
'og:title': Structured Outputs - Type-Safe JSON Responses from AI Models
'og:description': >-
  Enforce JSON Schema validation on AI model responses. Get consistent,
  type-safe outputs and avoid parsing errors with OpenRouter's structured output
  feature.
'og:image':
  type: url
  value: >-
    https://openrouter.ai/dynamic-og?title=Structured%20Outputs&description=Type-Safe%20JSON%20Responses%20from%20AI%20Models
'og:image:width': 1200
'og:image:height': 630
'twitter:card': summary_large_image
'twitter:site': '@OpenRouterAI'
noindex: false
nofollow: false
---

import { API_KEY_REF } from '../../../imports/constants';

OpenRouter supports structured outputs for compatible models, ensuring responses follow a specific JSON Schema format. This feature is particularly useful when you need consistent, well-formatted responses that can be reliably parsed by your application.

## Overview

Structured outputs allow you to:

- Enforce specific JSON Schema validation on model responses
- Get consistent, type-safe outputs
- Avoid parsing errors and hallucinated fields
- Simplify response handling in your application

## Using Structured Outputs

To use structured outputs, include a `response_format` parameter in your request, with `type` set to `json_schema` and the `json_schema` object containing your schema:

```typescript
{
  "messages": [
    { "role": "user", "content": "What's the weather like in London?" }
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "weather",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "City or location name"
          },
          "temperature": {
            "type": "number",
            "description": "Temperature in Celsius"
          },
          "conditions": {
            "type": "string",
            "description": "Weather conditions description"
          }
        },
        "required": ["location", "temperature", "conditions"],
        "additionalProperties": false
      }
    }
  }
}
```

The model will respond with a JSON object that strictly follows your schema:

```json
{
  "location": "London",
  "temperature": 18,
  "conditions": "Partly cloudy with light drizzle"
}
```

## Model Support

Structured outputs are supported by select models.

You can find a list of models that support structured outputs on the [models page](https://openrouter.ai/models?order=newest&supported_parameters=structured_outputs).

- OpenAI models (GPT-4o and later versions) [Docs](https://platform.openai.com/docs/guides/structured-outputs)
- All Fireworks provided models [Docs](https://docs.fireworks.ai/structured-responses/structured-response-formatting#structured-response-modes)

To ensure your chosen model supports structured outputs:

1. Check the model's supported parameters on the [models page](https://openrouter.ai/models)
2. Set `require_parameters: true` in your provider preferences (see [Provider Routing](/docs/features/provider-routing))
3. Include `response_format` and set `type: json_schema` in the required parameters

## Best Practices

1. **Include descriptions**: Add clear descriptions to your schema properties to guide the model

2. **Use strict mode**: Always set `strict: true` to ensure the model follows your schema exactly

## Example Implementation

Here's a complete example using the Fetch API:

<Template data={{
  API_KEY_REF,
  MODEL: 'openai/gpt-4'
}}>
<CodeGroup>

```typescript title="With TypeScript"
const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
  method: 'POST',
  headers: {
    Authorization: `Bearer {{API_KEY_REF}}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: '{{MODEL}}',
    messages: [
      { role: 'user', content: 'What is the weather like in London?' },
    ],
    response_format: {
      type: 'json_schema',
      json_schema: {
        name: 'weather',
        strict: true,
        schema: {
          type: 'object',
          properties: {
            location: {
              type: 'string',
              description: 'City or location name',
            },
            temperature: {
              type: 'number',
              description: 'Temperature in Celsius',
            },
            conditions: {
              type: 'string',
              description: 'Weather conditions description',
            },
          },
          required: ['location', 'temperature', 'conditions'],
          additionalProperties: false,
        },
      },
    },
  }),
});

const data = await response.json();
const weatherInfo = data.choices[0].message.content;
```

```python title="With Python"
import requests
import json

response = requests.post(
  "https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": f"Bearer {{API_KEY_REF}}",
    "Content-Type": "application/json",
  },

  json={
    "model": "{{MODEL}}",
    "messages": [
      {"role": "user", "content": "What is the weather like in London?"},
    ],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "weather",
        "strict": True,
        "schema": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "City or location name",
            },
            "temperature": {
              "type": "number",
              "description": "Temperature in Celsius",
            },
            "conditions": {
              "type": "string",
              "description": "Weather conditions description",
            },
          },
          "required": ["location", "temperature", "conditions"],
          "additionalProperties": False,
        },
      },
    },
  },
)

data = response.json()
weather_info = data["choices"][0]["message"]["content"]
```

</CodeGroup>

</Template>

## Streaming with Structured Outputs

Structured outputs are also supported with streaming responses. The model will stream valid partial JSON that, when complete, forms a valid response matching your schema.

To enable streaming with structured outputs, simply add `stream: true` to your request:

```typescript
{
  "stream": true,
  "response_format": {
    "type": "json_schema",
    // ... rest of your schema
  }
}
```

## Error Handling

When using structured outputs, you may encounter these scenarios:

1. **Model doesn't support structured outputs**: The request will fail with an error indicating lack of support
2. **Invalid schema**: The model will return an error if your JSON Schema is invalid


---
title: Images & PDFs
subtitle: How to send images and PDFs to OpenRouter
headline: OpenRouter Images & PDFs | Complete Documentation
canonical-url: 'https://openrouter.ai/docs/features/images-and-pdfs'
'og:site_name': OpenRouter Documentation
'og:title': OpenRouter Images & PDFs - Complete Documentation
'og:description': Sending images and PDFs to the OpenRouter API.
'og:image':
  type: url
  value: >-
    https://openrouter.ai/dynamic-og?title=OpenRouter%20Images%20&%20PDFs&description=Sending%20images%20and%20PDFs%20to%20the%20OpenRouter%20API.
'og:image:width': 1200
'og:image:height': 630
'twitter:card': summary_large_image
'twitter:site': '@OpenRouterAI'
noindex: false
nofollow: false
---

import {
  API_KEY_REF,
  DEFAULT_PDF_ENGINE,
  MISTRAL_OCR_USER_COST_PER_1K_PAGE as MISTRAL_OCR_COST,
  PDFParserEngine,
} from '../../../imports/constants';

OpenRouter supports sending images and PDFs via the API. This guide will show you how to work with both file types using our API.

Both images and PDFs also work in the chat room.

<Tip>You can send both PDF and images in the same request.</Tip>

## Image Inputs

Requests with images, to multimodel models, are available via the `/api/v1/chat/completions` API with a multi-part `messages` parameter. The `image_url` can either be a URL or a base64-encoded image. Note that multiple images can be sent in separate content array entries. The number of images you can send in a single request varies per provider and per model. Due to how the content is parsed, we recommend sending the text prompt first, then the images. If the images must come first, we recommend putting it in the system prompt.

### Using Image URLs

Here's how to send an image using a URL:

<Template data={{
  API_KEY_REF,
  MODEL: 'google/gemini-2.0-flash-001'
}}>
<CodeGroup>

```python
import requests
import json

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY_REF}",
    "Content-Type": "application/json"
}

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "What's in this image?"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
                }
            }
        ]
    }
]

payload = {
    "model": "{{MODEL}}",
    "messages": messages
}

response = requests.post(url, headers=headers, json=payload)
print(response.json())
```

```typescript
const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${API_KEY_REF}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: '{{MODEL}}',
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'text',
            text: "What's in this image?",
          },
          {
            type: 'image_url',
            image_url: {
              url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg',
            },
          },
        ],
      },
    ],
  }),
});

const data = await response.json();
console.log(data);
```

</CodeGroup>
</Template>

### Using Base64 Encoded Images

For locally stored images, you can send them using base64 encoding. Here's how to do it:

<Template data={{
  API_KEY_REF,
  MODEL: 'google/gemini-2.0-flash-001'
}}>
<CodeGroup>

```python
import requests
import json
import base64
from pathlib import Path

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY_REF}",
    "Content-Type": "application/json"
}

# Read and encode the image
image_path = "path/to/your/image.jpg"
base64_image = encode_image_to_base64(image_path)
data_url = f"data:image/jpeg;base64,{base64_image}"

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "What's in this image?"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": data_url
                }
            }
        ]
    }
]

payload = {
    "model": "{{MODEL}}",
    "messages": messages
}

response = requests.post(url, headers=headers, json=payload)
print(response.json())
```

```typescript
async function encodeImageToBase64(imagePath: string): Promise<string> {
  const imageBuffer = await fs.promises.readFile(imagePath);
  const base64Image = imageBuffer.toString('base64');
  return `data:image/jpeg;base64,${base64Image}`;
}

// Read and encode the image
const imagePath = 'path/to/your/image.jpg';
const base64Image = await encodeImageToBase64(imagePath);

const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${API_KEY_REF}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: '{{MODEL}}',
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'text',
            text: "What's in this image?",
          },
          {
            type: 'image_url',
            image_url: {
              url: base64Image,
            },
          },
        ],
      },
    ],
  }),
});

const data = await response.json();
console.log(data);
```

</CodeGroup>
</Template>

Supported image content types are:

- `image/png`
- `image/jpeg`
- `image/webp`

## PDF Support

OpenRouter supports PDF processing through the `/api/v1/chat/completions` API. PDFs can be sent as base64-encoded data URLs in the messages array, via the file content type. This feature works on **any** model on OpenRouter.

<Info>
  When a model supports file input natively, the PDF is passed directly to the
  model. When the model does not support file input natively, OpenRouter will
  parse the file and pass the parsed results to the requested model.
</Info>

Note that multiple PDFs can be sent in separate content array entries. The number of PDFs you can send in a single request varies per provider and per model. Due to how the content is parsed, we recommend sending the text prompt first, then the PDF. If the PDF must come first, we recommend putting it in the system prompt.

### Processing PDFs

Here's how to send and process a PDF:

<Template data={{
  API_KEY_REF,
  MODEL: 'google/gemma-3-27b-it',
  ENGINE: PDFParserEngine.PDFText,
  DEFAULT_PDF_ENGINE,
}}>
<CodeGroup>

```python
import requests
import json
import base64
from pathlib import Path

def encode_pdf_to_base64(pdf_path):
    with open(pdf_path, "rb") as pdf_file:
        return base64.b64encode(pdf_file.read()).decode('utf-8')

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY_REF}",
    "Content-Type": "application/json"
}

# Read and encode the PDF
pdf_path = "path/to/your/document.pdf"
base64_pdf = encode_pdf_to_base64(pdf_path)
data_url = f"data:application/pdf;base64,{base64_pdf}"

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "What are the main points in this document?"
            },
            {
                "type": "file",
                "file": {
                    "filename": "document.pdf",
                    "file_data": data_url
                }
            },
        ]
    }
]

# Optional: Configure PDF processing engine
# PDF parsing will still work even if the plugin is not explicitly set
plugins = [
    {
        "id": "file-parser",
        "pdf": {
            "engine": "{{ENGINE}}"  # defaults to "{{DEFAULT_PDF_ENGINE}}". See Pricing below
        }
    }
]

payload = {
    "model": "{{MODEL}}",
    "messages": messages,
    "plugins": plugins
}

response = requests.post(url, headers=headers, json=payload)
print(response.json())
```

```typescript
async function encodePDFToBase64(pdfPath: string): Promise<string> {
  const pdfBuffer = await fs.promises.readFile(pdfPath);
  const base64PDF = pdfBuffer.toString('base64');
  return `data:application/pdf;base64,${base64PDF}`;
}

// Read and encode the PDF
const pdfPath = 'path/to/your/document.pdf';
const base64PDF = await encodePDFToBase64(pdfPath);

const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${API_KEY_REF}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: '{{MODEL}}',
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'text',
            text: 'What are the main points in this document?',
          },
          {
            type: 'file',
            file: {
              filename: 'document.pdf',
              file_data: base64PDF,
            },
          },
        ],
      },
    ],
    // Optional: Configure PDF processing engine
    // PDF parsing will still work even if the plugin is not explicitly set
    plugins: [
      {
        id: 'file-parser',
        pdf: {
          engine: '{{ENGINE}}', // defaults to "{{DEFAULT_PDF_ENGINE}}". See Pricing below
        },
      },
    ],
  }),
});

const data = await response.json();
console.log(data);
```

</CodeGroup>
</Template>

### Pricing

OpenRouter provides several PDF processing engines:

1. <code>"{PDFParserEngine.MistralOCR}"</code>: Best for scanned documents or
   PDFs with images (${MISTRAL_OCR_COST.toString()} per 1,000 pages).
2. <code>"{PDFParserEngine.PDFText}"</code>: Best for well-structured PDFs with
   clear text content (Free).
3. <code>"{PDFParserEngine.Native}"</code>: Only available for models that
   support file input natively (charged as input tokens).

If you don't explicitly specify an engine, OpenRouter will default first to the model's native file processing capabilities, and if that's not available, we will use the <code>"{DEFAULT_PDF_ENGINE}"</code> engine.

To select an engine, use the plugin configuration:

<Template data={{
  API_KEY_REF,
  ENGINE: PDFParserEngine.MistralOCR,
}}>
<CodeGroup>

```python
plugins = [
    {
        "id": "file-parser",
        "pdf": {
            "engine": "{{ENGINE}}"
        }
    }
]
```

```typescript
{
  plugins: [
    {
      id: 'file-parser',
      pdf: {
        engine: '{{ENGINE}}',
      },
    },
  ],
}
```

</CodeGroup>
</Template>

### Skip Parsing Costs

When you send a PDF to the API, the response may include file annotations in the assistant's message. These annotations contain structured information about the PDF document that was parsed. By sending these annotations back in subsequent requests, you can avoid re-parsing the same PDF document multiple times, which saves both processing time and costs.

Here's how to reuse file annotations:

<Template data={{
  API_KEY_REF,
  MODEL: 'google/gemma-3-27b-it'
}}>
<CodeGroup>

```python
import requests
import json
import base64
from pathlib import Path

# First, encode and send the PDF
def encode_pdf_to_base64(pdf_path):
    with open(pdf_path, "rb") as pdf_file:
        return base64.b64encode(pdf_file.read()).decode('utf-8')

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY_REF}",
    "Content-Type": "application/json"
}

# Read and encode the PDF
pdf_path = "path/to/your/document.pdf"
base64_pdf = encode_pdf_to_base64(pdf_path)
data_url = f"data:application/pdf;base64,{base64_pdf}"

# Initial request with the PDF
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "What are the main points in this document?"
            },
            {
                "type": "file",
                "file": {
                    "filename": "document.pdf",
                    "file_data": data_url
                }
            },
        ]
    }
]

payload = {
    "model": "{{MODEL}}",
    "messages": messages
}

response = requests.post(url, headers=headers, json=payload)
response_data = response.json()

# Store the annotations from the response
file_annotations = None
if response_data.get("choices") and len(response_data["choices"]) > 0:
    if "annotations" in response_data["choices"][0]["message"]:
        file_annotations = response_data["choices"][0]["message"]["annotations"]

# Follow-up request using the annotations (without sending the PDF again)
if file_annotations:
    follow_up_messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What are the main points in this document?"
                },
                {
                    "type": "file",
                    "file": {
                        "filename": "document.pdf",
                        "file_data": data_url
                    }
                }
            ]
        },
        {
            "role": "assistant",
            "content": "The document contains information about...",
            "annotations": file_annotations
        },
        {
            "role": "user",
            "content": "Can you elaborate on the second point?"
        }
    ]

    follow_up_payload = {
        "model": "{{MODEL}}",
        "messages": follow_up_messages
    }

    follow_up_response = requests.post(url, headers=headers, json=follow_up_payload)
    print(follow_up_response.json())
```

```typescript
import fs from 'fs/promises';
import { fetch } from 'node-fetch';

async function encodePDFToBase64(pdfPath: string): Promise<string> {
  const pdfBuffer = await fs.readFile(pdfPath);
  const base64PDF = pdfBuffer.toString('base64');
  return `data:application/pdf;base64,${base64PDF}`;
}

// Initial request with the PDF
async function processDocument() {
  // Read and encode the PDF
  const pdfPath = 'path/to/your/document.pdf';
  const base64PDF = await encodePDFToBase64(pdfPath);

  const initialResponse = await fetch(
    'https://openrouter.ai/api/v1/chat/completions',
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${API_KEY_REF}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: '{{MODEL}}',
        messages: [
          {
            role: 'user',
            content: [
              {
                type: 'text',
                text: 'What are the main points in this document?',
              },
              {
                type: 'file',
                file: {
                  filename: 'document.pdf',
                  file_data: base64PDF,
                },
              },
            ],
          },
        ],
      }),
    },
  );

  const initialData = await initialResponse.json();

  // Store the annotations from the response
  let fileAnnotations = null;
  if (initialData.choices && initialData.choices.length > 0) {
    if (initialData.choices[0].message.annotations) {
      fileAnnotations = initialData.choices[0].message.annotations;
    }
  }

  // Follow-up request using the annotations (without sending the PDF again)
  if (fileAnnotations) {
    const followUpResponse = await fetch(
      'https://openrouter.ai/api/v1/chat/completions',
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${API_KEY_REF}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: '{{MODEL}}',
          messages: [
            {
              role: 'user',
              content: [
                {
                  type: 'text',
                  text: 'What are the main points in this document?',
                },
                {
                  type: 'file',
                  file: {
                    filename: 'document.pdf',
                    file_data: base64PDF,
                  },
                },
              ],
            },
            {
              role: 'assistant',
              content: 'The document contains information about...',
              annotations: fileAnnotations,
            },
            {
              role: 'user',
              content: 'Can you elaborate on the second point?',
            },
          ],
        }),
      },
    );

    const followUpData = await followUpResponse.json();
    console.log(followUpData);
  }
}

processDocument();
```

</CodeGroup>
</Template>

<Info>
  When you include the file annotations from a previous response in your
  subsequent requests, OpenRouter will use this pre-parsed information instead
  of re-parsing the PDF, which saves processing time and costs. This is
  especially beneficial for large documents or when using the `mistral-ocr`
  engine which incurs additional costs.
</Info>

### Response Format

The API will return a response in the following format:

```json
{
  "id": "gen-1234567890",
  "provider": "DeepInfra",
  "model": "google/gemma-3-27b-it",
  "object": "chat.completion",
  "created": 1234567890,
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "The document discusses..."
      }
    }
  ],
  "usage": {
    "prompt_tokens": 1000,
    "completion_tokens": 100,
    "total_tokens": 1100
  }
}
```
---
title: Web Search
subtitle: Model-agnostic grounding
headline: Web Search | Add Real-time Web Data to AI Model Responses
canonical-url: 'https://openrouter.ai/docs/features/web-search'
'og:site_name': OpenRouter Documentation
'og:title': Web Search - Real-time Web Grounding for AI Models
'og:description': >-
  Enable real-time web search capabilities in your AI model responses. Add
  factual, up-to-date information to any model's output with OpenRouter's web
  search feature.
'og:image':
  type: url
  value: >-
    https://openrouter.ai/dynamic-og?pathname=features/web-search&title=Web%20Search&description=Add%20real-time%20web%20data%20to%20any%20AI%20model%20response
'og:image:width': 1200
'og:image:height': 630
'twitter:card': summary_large_image
'twitter:site': '@OpenRouterAI'
noindex: false
nofollow: false
---

You can incorporate relevant web search results for _any_ model on OpenRouter by activating and customizing the `web` plugin, or by appending `:online` to the model slug:

```json
{
  "model": "openai/gpt-4o:online"
}
```

This is a shortcut for using the `web` plugin, and is exactly equivalent to:

```json
{
  "model": "openrouter/auto",
  "plugins": [{ "id": "web" }]
}
```

The web search plugin is powered by [Exa](https://exa.ai) and uses their ["auto"](https://docs.exa.ai/reference/how-exa-search-works#combining-neural-and-keyword-the-best-of-both-worlds-through-exa-auto-search) method (a combination of keyword search and embeddings-based web search) to find the most relevant results and augment/ground your prompt.

## Parsing web search results

Web search results for all models (including native-only models like Perplexity and OpenAI Online) are available in the API and standardized by OpenRouterto follow the same annotation schema in the [OpenAI Chat Completion Message type](https://platform.openai.com/docs/api-reference/chat/object):

```json
{
  "message": {
    "role": "assistant",
    "content": "Here's the latest news I found: ...",
    "annotations": [
      {
        "type": "url_citation",
        "url_citation": {
          "url": "https://www.example.com/web-search-result",
          "title": "Title of the web search result",
          "content": "Content of the web search result", // Added by OpenRouter if available
          "start_index": 100, // The index of the first character of the URL citation in the message.
          "end_index": 200 // The index of the last character of the URL citation in the message.
        }
      }
    ]
  }
}
```

## Customizing the Web Plugin

The maximum results allowed by the web plugin and the prompt used to attach them to your message stream can be customized:

```json
{
  "model": "openai/gpt-4o:online",
  "plugins": [
    {
      "id": "web",
      "max_results": 1, // Defaults to 5
      "search_prompt": "Some relevant web results:" // See default below
    }
  ]
}
```

By default, the web plugin uses the following search prompt, using the current date:

```
A web search was conducted on `date`. Incorporate the following web search results into your response.

IMPORTANT: Cite them using markdown links named using the domain of the source.
Example: [nytimes.com](https://nytimes.com/some-page).
```

## Pricing

The web plugin uses your OpenRouter credits and charges _\$4 per 1000 results_. By default, `max_results` set to 5, this comes out to a maximum of \$0.02 per request, in addition to the LLM usage for the search result prompt tokens.

## Non-plugin Web Search

Some models have built-in web search. These models charge a fee based on the search context size, which determines how much search data is retrieved and processed for a query.

### Search Context Size Thresholds

Search context can be 'low', 'medium', or 'high' and determines how much search context is retrieved for a query:

- **Low**: Minimal search context, suitable for basic queries
- **Medium**: Moderate search context, good for general queries
- **High**: Extensive search context, ideal for detailed research

### Specifying Search Context Size

You can specify the search context size in your API request using the `web_search_options` parameter:

```json
{
  "model": "openai/gpt-4.1",
  "messages": [
    {
      "role": "user",
      "content": "What are the latest developments in quantum computing?"
    }
  ],
  "web_search_options": {
    "search_context_size": "high"
  }
}
```

### OpenAI Model Pricing

For GPT-4, GPT-4o, and GPT-4 Omni Models:

| Search Context Size | Price per 1000 Requests |
| ------------------- | ----------------------- |
| Low                 | $30.00                  |
| Medium              | $35.00                  |
| High                | $50.00                  |

For GPT-4 Mini, GPT-4o Mini, and GPT-4 Omni Mini Models:

| Search Context Size | Price per 1000 Requests |
| ------------------- | ----------------------- |
| Low                 | $25.00                  |
| Medium              | $27.50                  |
| High                | $30.00                  |

### Perplexity Model Pricing

For Sonar and SonarReasoning:

| Search Context Size | Price per 1000 Requests |
| ------------------- | ----------------------- |
| Low                 | $5.00                   |
| Medium              | $8.00                   |
| High                | $12.00                  |

For SonarPro and SonarReasoningPro:

| Search Context Size | Price per 1000 Requests |
| ------------------- | ----------------------- |
| Low                 | $6.00                   |
| Medium              | $10.00                  |
| High                | $14.00                  |

<Note title='Pricing Documentation'>

For more detailed information about pricing models, refer to the official documentation:

- [OpenAI Pricing](https://platform.openai.com/docs/pricing#web-search)
- [Perplexity Pricing](https://docs.perplexity.ai/guides/pricing)

</Note>


---
title: Provisioning API Keys
subtitle: Manage API keys programmatically
headline: Provisioning API Keys | Programmatic Control of OpenRouter API Keys
canonical-url: 'https://openrouter.ai/docs/features/provisioning-api-keys'
'og:site_name': OpenRouter Documentation
'og:title': Provisioning API Keys - Programmatic Control of OpenRouter API Keys
'og:description': >-
  Manage OpenRouter API keys programmatically through dedicated management
  endpoints. Create, read, update, and delete API keys for automated key
  distribution and control.
'og:image':
  type: url
  value: >-
    https://openrouter.ai/dynamic-og?pathname=features/provisioning-api-keys&title=Provisioning%20API%20Keys&description=Programmatically%20manage%20OpenRouter%20API%20keys
'og:image:width': 1200
'og:image:height': 630
'twitter:card': summary_large_image
'twitter:site': '@OpenRouterAI'
noindex: false
nofollow: false
---

OpenRouter provides endpoints to programmatically manage your API keys, enabling key creation and management for applications that need to distribute or rotate keys automatically.

## Creating a Provisioning API Key

To use the key management API, you first need to create a Provisioning API key:

1. Go to the [Provisioning API Keys page](https://openrouter.ai/settings/provisioning-keys)
2. Click "Create New Key"
3. Complete the key creation process

Provisioning keys cannot be used to make API calls to OpenRouter's completion endpoints - they are exclusively for key management operations.

## Use Cases

Common scenarios for programmatic key management include:

- **SaaS Applications**: Automatically create unique API keys for each customer instance
- **Key Rotation**: Regularly rotate API keys for security compliance
- **Usage Monitoring**: Track key usage and automatically disable keys that exceed limits

## Example Usage

All key management endpoints are under `/api/v1/keys` and require a Provisioning API key in the Authorization header.

<CodeGroup>

```python title="Python"
import requests

PROVISIONING_API_KEY = "your-provisioning-key"
BASE_URL = "https://openrouter.ai/api/v1/keys"

# List the most recent 100 API keys
response = requests.get(
    BASE_URL,
    headers={
        "Authorization": f"Bearer {PROVISIONING_API_KEY}",
        "Content-Type": "application/json"
    }
)

# You can paginate using the offset parameter
response = requests.get(
    f"{BASE_URL}?offset=100",
    headers={
        "Authorization": f"Bearer {PROVISIONING_API_KEY}",
        "Content-Type": "application/json"
    }
)

# Create a new API key
response = requests.post(
    f"{BASE_URL}/",
    headers={
        "Authorization": f"Bearer {PROVISIONING_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "name": "Customer Instance Key",
        "label": "customer-123",
        "limit": 1000  # Optional credit limit
    }
)

# Get a specific key
key_hash = "<YOUR_KEY_HASH>"
response = requests.get(
    f"{BASE_URL}/{key_hash}",
    headers={
        "Authorization": f"Bearer {PROVISIONING_API_KEY}",
        "Content-Type": "application/json"
    }
)

# Update a key
response = requests.patch(
    f"{BASE_URL}/{key_hash}",
    headers={
        "Authorization": f"Bearer {PROVISIONING_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "name": "Updated Key Name",
        "disabled": True  # Disable the key
    }
)

# Delete a key
response = requests.delete(
    f"{BASE_URL}/{key_hash}",
    headers={
        "Authorization": f"Bearer {PROVISIONING_API_KEY}",
        "Content-Type": "application/json"
    }
)
```

```typescript title="TypeScript"
const PROVISIONING_API_KEY = 'your-provisioning-key';
const BASE_URL = 'https://openrouter.ai/api/v1/keys';

// List the most recent 100 API keys
const listKeys = await fetch(BASE_URL, {
  headers: {
    Authorization: `Bearer ${PROVISIONING_API_KEY}`,
    'Content-Type': 'application/json',
  },
});

// You can paginate using the `offset` query parameter
const listKeys = await fetch(`${BASE_URL}?offset=100`, {
  headers: {
    Authorization: `Bearer ${PROVISIONING_API_KEY}`,
    'Content-Type': 'application/json',
  },
});

// Create a new API key
const createKey = await fetch(`${BASE_URL}`, {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${PROVISIONING_API_KEY}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    name: 'Customer Instance Key',
    label: 'customer-123',
    limit: 1000, // Optional credit limit
  }),
});

// Get a specific key
const keyHash = '<YOUR_KEY_HASH>';
const getKey = await fetch(`${BASE_URL}/${keyHash}`, {
  headers: {
    Authorization: `Bearer ${PROVISIONING_API_KEY}`,
    'Content-Type': 'application/json',
  },
});

// Update a key
const updateKey = await fetch(`${BASE_URL}/${keyHash}`, {
  method: 'PATCH',
  headers: {
    Authorization: `Bearer ${PROVISIONING_API_KEY}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    name: 'Updated Key Name',
    disabled: true, // Disable the key
  }),
});

// Delete a key
const deleteKey = await fetch(`${BASE_URL}/${keyHash}`, {
  method: 'DELETE',
  headers: {
    Authorization: `Bearer ${PROVISIONING_API_KEY}`,
    'Content-Type': 'application/json',
  },
});
```

</CodeGroup>

## Response Format

API responses return JSON objects containing key information:

```json
{
  "data": [
    {
      "created_at": "2025-02-19T20:52:27.363244+00:00",
      "updated_at": "2025-02-19T21:24:11.708154+00:00",
      "hash": "<YOUR_KEY_HASH>",
      "label": "sk-or-v1-customkey",
      "name": "Customer Key",
      "disabled": false,
      "limit": 10,
      "usage": 0
    }
  ]
}
```

When creating a new key, the response will include the key string itself.



---
title: Parameters
headline: API Parameters | Configure OpenRouter API Requests
canonical-url: 'https://openrouter.ai/docs/api-reference/parameters'
'og:site_name': OpenRouter Documentation
'og:title': API Parameters - Complete Guide to Request Configuration
'og:description': >-
  Learn about all available parameters for OpenRouter API requests. Configure
  temperature, max tokens, top_p, and other model-specific settings.
'og:image':
  type: url
  value: >-
    https://openrouter.ai/dynamic-og?title=API%20Parameters&description=Complete%20guide%20to%20request%20configuration
'og:image:width': 1200
'og:image:height': 630
'twitter:card': summary_large_image
'twitter:site': '@OpenRouterAI'
noindex: false
nofollow: false
---

Sampling parameters shape the token generation process of the model. You may send any parameters from the following list, as well as others, to OpenRouter.

OpenRouter will default to the values listed below if certain parameters are absent from your request (for example, `temperature` to 1.0). We will also transmit some provider-specific parameters, such as `safe_prompt` for Mistral or `raw_mode` for Hyperbolic directly to the respective providers if specified.

Please refer to the model’s provider section to confirm which parameters are supported. For detailed guidance on managing provider-specific parameters, [click here](/docs/features/provider-routing#requiring-providers-to-support-all-parameters-beta).

## Temperature

- Key: `temperature`

- Optional, **float**, 0.0 to 2.0

- Default: 1.0

- Explainer Video: [Watch](https://youtu.be/ezgqHnWvua8)

This setting influences the variety in the model's responses. Lower values lead to more predictable and typical responses, while higher values encourage more diverse and less common responses. At 0, the model always gives the same response for a given input.

## Top P

- Key: `top_p`

- Optional, **float**, 0.0 to 1.0

- Default: 1.0

- Explainer Video: [Watch](https://youtu.be/wQP-im_HInk)

This setting limits the model's choices to a percentage of likely tokens: only the top tokens whose probabilities add up to P. A lower value makes the model's responses more predictable, while the default setting allows for a full range of token choices. Think of it like a dynamic Top-K.

## Top K

- Key: `top_k`

- Optional, **integer**, 0 or above

- Default: 0

- Explainer Video: [Watch](https://youtu.be/EbZv6-N8Xlk)

This limits the model's choice of tokens at each step, making it choose from a smaller set. A value of 1 means the model will always pick the most likely next token, leading to predictable results. By default this setting is disabled, making the model to consider all choices.

## Frequency Penalty

- Key: `frequency_penalty`

- Optional, **float**, -2.0 to 2.0

- Default: 0.0

- Explainer Video: [Watch](https://youtu.be/p4gl6fqI0_w)

This setting aims to control the repetition of tokens based on how often they appear in the input. It tries to use less frequently those tokens that appear more in the input, proportional to how frequently they occur. Token penalty scales with the number of occurrences. Negative values will encourage token reuse.

## Presence Penalty

- Key: `presence_penalty`

- Optional, **float**, -2.0 to 2.0

- Default: 0.0

- Explainer Video: [Watch](https://youtu.be/MwHG5HL-P74)

Adjusts how often the model repeats specific tokens already used in the input. Higher values make such repetition less likely, while negative values do the opposite. Token penalty does not scale with the number of occurrences. Negative values will encourage token reuse.

## Repetition Penalty

- Key: `repetition_penalty`

- Optional, **float**, 0.0 to 2.0

- Default: 1.0

- Explainer Video: [Watch](https://youtu.be/LHjGAnLm3DM)

Helps to reduce the repetition of tokens from the input. A higher value makes the model less likely to repeat tokens, but too high a value can make the output less coherent (often with run-on sentences that lack small words). Token penalty scales based on original token's probability.

## Min P

- Key: `min_p`

- Optional, **float**, 0.0 to 1.0

- Default: 0.0

Represents the minimum probability for a token to be
  considered, relative to the probability of the most likely token. (The value changes depending on the confidence level of the most probable token.) If your Min-P is set to 0.1, that means it will only allow for tokens that are at least 1/10th as probable as the best possible option.

## Top A

- Key: `top_a`

- Optional, **float**, 0.0 to 1.0

- Default: 0.0

Consider only the top tokens with "sufficiently high" probabilities based on the probability of the most likely token. Think of it like a dynamic Top-P. A lower Top-A value focuses the choices based on the highest probability token but with a narrower scope. A higher Top-A value does not necessarily affect the creativity of the output, but rather refines the filtering process based on the maximum probability.

## Seed

- Key: `seed`

- Optional, **integer**

If specified, the inferencing will sample deterministically, such that repeated requests with the same seed and parameters should return the same result. Determinism is not guaranteed for some models.

## Max Tokens

- Key: `max_tokens`

- Optional, **integer**, 1 or above

This sets the upper limit for the number of tokens the model can generate in response. It won't produce more than this limit. The maximum value is the context length minus the prompt length.

## Logit Bias

- Key: `logit_bias`

- Optional, **map**

Accepts a JSON object that maps tokens (specified by their token ID in the tokenizer) to an associated bias value from -100 to 100. Mathematically, the bias is added to the logits generated by the model prior to sampling. The exact effect will vary per model, but values between -1 and 1 should decrease or increase likelihood of selection; values like -100 or 100 should result in a ban or exclusive selection of the relevant token.

## Logprobs

- Key: `logprobs`

- Optional, **boolean**

Whether to return log probabilities of the output tokens or not. If true, returns the log probabilities of each output token returned.

## Top Logprobs

- Key: `top_logprobs`

- Optional, **integer**

An integer between 0 and 20 specifying the number of most likely tokens to return at each token position, each with an associated log probability. logprobs must be set to true if this parameter is used.

## Response Format

- Key: `response_format`

- Optional, **map**

Forces the model to produce specific output format. Setting to `{ "type": "json_object" }` enables JSON mode, which guarantees the message the model generates is valid JSON.

  **Note**: when using JSON mode, you should also instruct the model to produce JSON yourself via a system or user message.

## Structured Outputs

- Key: `structured_outputs`

- Optional, **boolean**

If the model can return structured outputs using response_format json_schema.

## Stop

- Key: `stop`

- Optional, **array**

Stop generation immediately if the model encounter any token specified in the stop array.

## Tools

- Key: `tools`

- Optional, **array**

Tool calling parameter, following OpenAI's tool calling request shape. For non-OpenAI providers, it will be transformed accordingly. [Click here to learn more about tool calling](/docs/requests#tool-calls)

## Tool Choice

- Key: `tool_choice`

- Optional, **array**

Controls which (if any) tool is called by the model. 'none' means the model will not call any tool and instead generates a message. 'auto' means the model can pick between generating a message or calling one or more tools. 'required' means the model must call one or more tools. Specifying a particular tool via `{"type": "function", "function": {"name": "my_function"}}` forces the model to call that tool.


---
title: Errors
subtitle: API Errors
headline: API Error Handling | OpenRouter Error Documentation
canonical-url: 'https://openrouter.ai/docs/api-reference/errors'
'og:site_name': OpenRouter Documentation
'og:title': API Error Handling - Complete Guide to OpenRouter Errors
'og:description': >-
  Learn how to handle errors in OpenRouter API interactions. Comprehensive guide
  to error codes, messages, and best practices for error handling.
'og:image':
  type: url
  value: >-
    https://openrouter.ai/dynamic-og?title=API%20Error%20Handling%20-Errors&description=Learn%20how%20to%20handle%20errors%20in%20OpenRouter%20API%20interactions.%20Comprehensive%20guide%20to%20error%20codes,%20messages,%20and%20best%20practices%20for%20error%20handling.
'og:image:width': 1200
'og:image:height': 630
'twitter:card': summary_large_image
'twitter:site': '@OpenRouterAI'
noindex: false
nofollow: false
---

import { HTTPStatus } from '../../../imports/constants';

For errors, OpenRouter returns a JSON response with the following shape:

```typescript
type ErrorResponse = {
  error: {
    code: number;
    message: string;
    metadata?: Record<string, unknown>;
  };
};
```

The HTTP Response will have the same status code as `error.code`, forming a request error if:

- Your original request is invalid
- Your API key/account is out of credits

Otherwise, the returned HTTP response status will be <code>{HTTPStatus.S200_OK}</code> and any error occurred while the LLM is producing the output will be emitted in the response body or as an SSE data event.

Example code for printing errors in JavaScript:

```typescript
const request = await fetch('https://openrouter.ai/...');
console.log(request.status); // Will be an error code unless the model started processing your request
const response = await request.json();
console.error(response.error?.status); // Will be an error code
console.error(response.error?.message);
```

## Error Codes

- **{HTTPStatus.S400_Bad_Request}**: Bad Request (invalid or missing params, CORS)
- **{HTTPStatus.S401_Unauthorized}**: Invalid credentials (OAuth session expired, disabled/invalid API key)
- **{HTTPStatus.S402_Payment_Required}**: Your account or API key has insufficient credits. Add more credits and retry the request.
- **{HTTPStatus.S403_Forbidden}**: Your chosen model requires moderation and your input was flagged
- **{HTTPStatus.S408_Request_Timeout}**: Your request timed out
- **{HTTPStatus.S429_Too_Many_Requests}**: You are being rate limited
- **{HTTPStatus.S502_Bad_Gateway}**: Your chosen model is down or we received an invalid response from it
- **{HTTPStatus.S503_Service_Unavailable}**: There is no available model provider that meets your routing requirements

## Moderation Errors

If your input was flagged, the `error.metadata` will contain information about the issue. The shape of the metadata is as follows:

```typescript
type ModerationErrorMetadata = {
  reasons: string[]; // Why your input was flagged
  flagged_input: string; // The text segment that was flagged, limited to 100 characters. If the flagged input is longer than 100 characters, it will be truncated in the middle and replaced with ...
  provider_name: string; // The name of the provider that requested moderation
  model_slug: string;
};
```

## Provider Errors

If the model provider encounters an error, the `error.metadata` will contain information about the issue. The shape of the metadata is as follows:

```typescript
type ProviderErrorMetadata = {
  provider_name: string; // The name of the provider that encountered the error
  raw: unknown; // The raw error from the provider
};
```

## When No Content is Generated

Occasionally, the model may not generate any content. This typically occurs when:

- The model is warming up from a cold start
- The system is scaling up to handle more requests

Warm-up times usually range from a few seconds to a few minutes, depending on the model and provider.

If you encounter persistent no-content issues, consider implementing a simple retry mechanism or trying again with a different provider or model that has more recent activity.

Additionally, be aware that in some cases, you may still be charged for the prompt processing cost by the upstream provider, even if no content is generated.


# API Reference
Authentication
Exchange authorization code for API key

POST
https://openrouter.ai/api/v1/auth/keys
POST
/api/v1/auth/keys

Python

import requests
url = "https://openrouter.ai/api/v1/auth/keys"
payload = { "code": "code" }
headers = {"Content-Type": "application/json"}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
Try it
200
Successful

{
  "key": "key",
  "user_id": "user_id"
}
Exchange an authorization code from the PKCE flow for a user-controlled API key

Request
This endpoint expects an object.
code
string
Required
The authorization code received from the OAuth redirect

code_verifier
string
Optional
The code verifier if code_challenge was used in the authorization request

code_challenge_method
enum
Optional
The method used to generate the code challenge

Allowed values:
S256
plain
Response
Successfully exchanged code for an API key

key
string
The API key to use for OpenRouter requests

user_id
string
Optional
User ID associated with the API key

Errors

400
Post Auth Keys Request Bad Request Error

403
Post Auth Keys Request Forbidden Error

405
Post Auth Keys Request Method Not Allowed Error


List available models

GET
https://openrouter.ai/api/v1/models
GET
/api/v1/models

Python

import requests
url = "https://openrouter.ai/api/v1/models"
response = requests.get(url)
print(response.json())
Try it
200
Retrieved

{
  "data": [
    {
      "id": "id",
      "name": "name",
      "created": 1741818122,
      "description": "description",
      "architecture": {
        "input_modalities": [
          "text",
          "image"
        ],
        "output_modalities": [
          "text"
        ],
        "tokenizer": "GPT"
      },
      "top_provider": {
        "is_moderated": true
      },
      "pricing": {
        "prompt": "0.0000007",
        "completion": "0.0000007",
        "image": "0",
        "request": "0",
        "input_cache_read": "0",
        "input_cache_write": "0",
        "web_search": "0",
        "internal_reasoning": "0"
      },
      "context_length": 128000,
      "hugging_face_id": "hugging_face_id",
      "per_request_limits": {
        "key": "value"
      },
      "supported_parameters": [
        "supported_parameters"
      ]
    }
  ]
}
Returns a list of models available through the API. Note: supported_parameters is a union of all parameters supported by all providers for this model. There may not be a single provider which offers all of the listed parameters for a model.

Response
List of available models

data
list of objects

Hide 11 properties
id
string
name
string
created
double
description
string
architecture
object

Show 4 properties
top_provider
object

Show 3 properties
pricing
object

Show 8 properties
context_length
double
Optional
hugging_face_id
string
Optional
per_request_limits
map from strings to any
Optional
supported_parameters
list of strings
Optional

API Reference
List endpoints for a model

GET
https://openrouter.ai/api/v1/models/:author/:slug/endpoints
GET
/api/v1/models/:author/:slug/endpoints

Python

import requests
url = "https://openrouter.ai/api/v1/models/author/slug/endpoints"
response = requests.get(url)
print(response.json())
Try it
200
Retrieved

{
  "data": {
    "id": "id",
    "name": "name",
    "created": 1.1,
    "description": "description",
    "architecture": {
      "input_modalities": [
        "text",
        "image"
      ],
      "output_modalities": [
        "text"
      ],
      "tokenizer": "tokenizer",
      "instruct_type": "instruct_type"
    },
    "endpoints": [
      {
        "name": "name",
        "context_length": 1.1,
        "pricing": {
          "request": "request",
          "image": "image",
          "prompt": "prompt",
          "completion": "completion"
        },
        "provider_name": "provider_name",
        "supported_parameters": [
          "supported_parameters"
        ]
      }
    ]
  }
}
Path parameters
author
string
Required
slug
string
Required
Response
List of endpoints for the model

data
object

Hide 6 properties
id
string
name
string
created
double
description
string
architecture
object

Hide 4 properties
input_modalities
list of strings
output_modalities
list of strings
tokenizer
string
Optional
instruct_type
string
Optional
endpoints
list of objects

Hide 9 properties
name
string
context_length
double
pricing
object

Hide 4 properties
request
string
image
string
prompt
string
completion
string
provider_name
string
supported_parameters
list of strings
quantization
string
Optional
max_completion_tokens
double
Optional
max_prompt_tokens
double
Optional
status
string
Optional


# AVAILABLE MODELS

anthropic/claude-sonnet-4

google/gemini-2.5-flash-preview-05-20:thinking

google/gemini-2.5-pro-preview

google/gemini-2.5-pro-exp-03-25

google/gemini-pro-1.5

google/gemini-2.0-flash-exp:free

google/gemini-2.0-flash-001

openai/chatgpt-4o-latest

meta-llama/llama-4-maverick

meta-llama/llama-3.3-70b-instruct

meta-llama/llama-4-scout

meta-llama/llama-3.1-70b-instruct

deepseek/deepseek-chat-v3-0324:free

deepseek/deepseek-r1-0528:free

deepseek/deepseek-chat-v3-0324

deepseek/deepseek-r1:free

deepseek/deepseek-chat

perplexity/sonar-deep-research

agentica-org/deepcoder-14b-preview:free