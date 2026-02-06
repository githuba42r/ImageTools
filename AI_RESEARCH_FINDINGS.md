# OpenRouter.ai AI Research Findings

## Research Date
February 6, 2026

## Executive Summary

This document contains research findings on OpenRouter.ai's API capabilities, OAuth2 PKCE implementation, and recommended AI models for background removal and image manipulation features in the Image Tools application.

---

## 1. OPENROUTER.AI API OVERVIEW

### API Base URL
- Production: `https://openrouter.ai/api/v1`
- Models Endpoint: `https://openrouter.ai/api/v1/models`
- Chat Completions: `https://openrouter.ai/api/v1/chat/completions`

### Authentication Methods
1. **API Key** (Direct): Bearer token in Authorization header
2. **OAuth2 PKCE** (User-controlled): User authenticates and grants access

### Key Features
- Unified API for 300+ AI models
- Automatic model fallback and routing
- Support for vision models (text + image input)
- Support for image generation models
- Multimodal inputs: text, images, PDFs, audio, video
- Streaming responses
- Prompt caching
- Structured outputs
- Tool/function calling
- Zero data retention option

---

## 2. OAUTH2 PKCE IMPLEMENTATION

### Flow Overview

**Step 1: Redirect User to OpenRouter**
```
https://openrouter.ai/auth?callback_url=<YOUR_CALLBACK>&code_challenge=<CHALLENGE>&code_challenge_method=S256
```

Parameters:
- `callback_url`: Your application's OAuth callback URL
- `code_challenge`: SHA-256 hash of code_verifier (base64url encoded)
- `code_challenge_method`: "S256" (recommended) or "plain"

**Step 2: User Authorizes**
- User logs into OpenRouter account
- Grants permission to your application
- Redirected back to your callback URL with `code` parameter

**Step 3: Exchange Code for API Key**
POST to `https://openrouter.ai/api/v1/auth/keys`
```json
{
  "code": "<CODE_FROM_QUERY_PARAM>",
  "code_verifier": "<ORIGINAL_CODE_VERIFIER>",
  "code_challenge_method": "S256"
}
```

Response:
```json
{
  "key": "sk-or-v1-..."
}
```

### Implementation Requirements

**Frontend (JavaScript):**
```javascript
// Generate code verifier and challenge
import { Buffer } from 'buffer';

async function createSHA256CodeChallenge(verifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return Buffer.from(hash).toString('base64url');
}

// Store verifier in session/local storage
const codeVerifier = generateRandomString(128);
const codeChallenge = await createSHA256CodeChallenge(codeVerifier);
```

**Backend (Python):**
```python
import hashlib
import base64
import secrets

def generate_code_verifier():
    return base64.urlsafe_b64encode(secrets.token_bytes(96)).decode('utf-8').rstrip('=')

def create_code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
```

### Error Codes
- `400 Invalid code_challenge_method`: Method mismatch between steps
- `403 Invalid code or code_verifier`: Verification failed
- `405 Method Not Allowed`: Wrong HTTP method

### Security Considerations
1. Store `code_verifier` securely (session storage, not cookies)
2. Validate redirect URLs to prevent phishing
3. Use HTTPS for all requests
4. Implement CSRF protection on callback
5. Store received API key encrypted in database

---

## 3. IMAGE INPUT CAPABILITIES

### Vision Models Support
OpenRouter supports sending images to vision models through the chat completions API.

**Supported Input Formats:**
- Image URLs (public or signed)
- Base64-encoded images (data URLs)
- Formats: PNG, JPEG, WebP, GIF

**API Structure:**
```json
{
  "model": "google/gemini-3-flash-preview",
  "messages": [
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
            "url": "data:image/jpeg;base64,..."
          }
        }
      ]
    }
  ]
}
```

### Base64 Encoding for Local Images
```python
import base64

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_image}"
```

---

## 4. IMAGE GENERATION CAPABILITIES

### Overview
Some models can generate images when `modalities` parameter includes "image".

**API Structure:**
```json
{
  "model": "google/gemini-2.5-flash-image-preview",
  "messages": [
    {
      "role": "user",
      "content": "Generate a sunset over mountains"
    }
  ],
  "modalities": ["image", "text"]
}
```

**Response Format:**
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "I've generated an image...",
        "images": [
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/png;base64,..."
            }
          }
        ]
      }
    }
  ]
}
```

### Image Configuration Options
- `aspect_ratio`: "1:1", "16:9", "9:16", "4:3", "3:4", etc.
- `image_size`: "1K", "2K", "4K"

---

## 5. RECOMMENDED MODELS FOR BACKGROUND REMOVAL

### Analysis
Background removal is a specialized task. OpenRouter doesn't have dedicated background removal models, but we can use vision-capable models combined with image generation to achieve this.

### Approach: Vision + Image Generation Pipeline

**Option 1: Two-Step Process**
1. **Vision Model** analyzes image and identifies subject
2. **Image Generation Model** recreates subject on transparent background

**Option 2: Alternative Services**
For true background removal, we should consider:
- External API: Remove.bg API
- Python Library: rembg (uses u2net model)
- Self-hosted model: BRIA RMBG or MODNet

### Recommended Implementation for Stage 3

**Best Approach: Use rembg Python Library**
- Open source (MIT license)
- No API costs
- Fast processing
- High quality results
- Self-contained

```python
from rembg import remove
from PIL import Image

def remove_background(image_path, output_path):
    input_image = Image.open(image_path)
    output_image = remove(input_image)
    output_image.save(output_path, 'PNG')
```

**Why not OpenRouter for background removal?**
- OpenRouter excels at vision + text generation
- Background removal requires pixel-level segmentation
- Better handled by specialized computer vision models
- rembg is free, fast, and produces excellent results

**AI Enhancement (Optional):**
After rembg removes background, use OpenRouter vision models to:
- Refine edges
- Adjust lighting
- Suggest improvements

### Alternative: Remove.bg API Integration
If user prefers cloud-based solution:
- API: https://remove.bg/api
- Cost: ~$0.20 per image (paid plans)
- Very high quality
- No local processing needed

**Recommendation:** Implement rembg for Stage 3, add Remove.bg as optional premium feature later.

---

## 6. RECOMMENDED MODELS FOR AI IMAGE MANIPULATION CHAT

### Top Vision + Chat Models

#### 1. Google Gemini 3 Flash Preview (Recommended)
**Model ID:** `google/gemini-3-flash-preview`

**Capabilities:**
- Multimodal: text, image, audio, video, PDF input
- Text output with reasoning
- 1M token context window
- Fast inference
- Strong vision understanding
- Tool use support

**Pricing:**
- Prompt: $0.50 per 1M tokens ($0.0000005/token)
- Completion: $3.00 per 1M tokens ($0.000003/token)
- Image: $0.50 per 1M tokens
- Internal reasoning: $3.00 per 1M tokens

**Why Recommended:**
- Best balance of cost, speed, and quality
- Excellent at understanding image manipulation requests
- Strong multi-turn conversation
- Low latency for interactive chat
- Configurable reasoning levels

**Use Cases:**
- "Make this image look like a watercolor painting"
- "Adjust the colors to be warmer"
- "Add a vintage filter effect"
- "Crop to focus on the main subject"

#### 2. Anthropic Claude Opus 4.6 (Premium Option)
**Model ID:** `anthropic/claude-opus-4.6`

**Capabilities:**
- Text + image input
- Text output
- 1M token context window
- Extended thinking/reasoning
- Superior contextual understanding

**Pricing:**
- Prompt: $5.00 per 1M tokens ($0.000005/token)
- Completion: $25.00 per 1M tokens ($0.000025/token)
- Web search: $0.01 per search
- Prompt caching available

**Why Recommended:**
- Highest quality reasoning
- Best for complex multi-step manipulations
- Excellent at understanding nuanced requests
- Strong at creative interpretations

**Use Cases:**
- Complex artistic transformations
- Multi-step editing workflows
- Detailed style transfers
- Professional-grade adjustments

#### 3. Google Gemini 2 Flash (Budget Option)
**Model ID:** `google/gemini-2.5-flash`

**Capabilities:**
- Multimodal input
- Fast inference
- Good vision understanding
- Lower cost

**Pricing:**
- Prompt: $0.075 per 1M tokens
- Completion: $0.30 per 1M tokens
- Image: $0.04 per image

**Why Recommended:**
- Most affordable option
- Still very capable for common tasks
- Fast response times
- Good for basic manipulations

#### 4. Mistral Pixtral Large (Open Source)
**Model ID:** `mistralai/pixtral-large-2411`

**Capabilities:**
- Text + image input
- 128K context window
- Open source foundation

**Pricing:**
- Prompt: $2.00 per 1M tokens
- Completion: $6.00 per 1M tokens

**Why Recommended:**
- Open source transparency
- Good vision capabilities
- Moderate pricing
- European AI option

### Comparison Table

| Model | Cost/1M Tokens | Speed | Quality | Best For |
|-------|---------------|-------|---------|----------|
| Gemini 3 Flash | $0.50-$3.00 | Fast | Excellent | General use (Default) |
| Claude Opus 4.6 | $5.00-$25.00 | Medium | Superior | Complex tasks |
| Gemini 2 Flash | $0.08-$0.30 | Very Fast | Good | Budget-conscious |
| Pixtral Large | $2.00-$6.00 | Medium | Very Good | Open source preference |

### Implementation Strategy

**Default Model:** `google/gemini-3-flash-preview`
- Best all-around choice
- Excellent for 90% of use cases
- Good balance of cost and performance

**Allow User Selection:**
- Let users choose model in settings
- Display cost per request
- Show model capabilities and tags

**Model Selector UI:**
```
Model: [Gemini 3 Flash (Recommended) ▼]

Description: High speed, high value thinking model designed for 
             agentic workflows and multi-turn chat.

Tags: vision, chat, reasoning, multimodal

Estimated Cost: ~$0.01-0.05 per conversation turn

[Select Model]
```

---

## 7. IMAGE MANIPULATION APPROACH

### How to Use Vision Models for Image Manipulation

Since OpenRouter models generate text (and some generate images), we need a hybrid approach:

#### Approach A: Text Instructions → Local Processing
1. User: "Make this image warmer"
2. AI analyzes image and generates instructions:
   ```json
   {
     "operation": "adjust_color_temperature",
     "parameters": {
       "temperature": "+20",
       "tint": "+5"
     }
   }
   ```
3. Backend applies transformation using Pillow

**Pros:** Fast, predictable, low cost
**Cons:** Limited to predefined operations

#### Approach B: Image Generation
1. User: "Make this look like a watercolor painting"
2. AI generates new image with style applied
3. Replace original with generated version

**Pros:** Unlimited creative possibilities
**Cons:** Slower, higher cost, may lose details

#### Approach C: Hybrid (Recommended)
1. Use text instructions for technical adjustments (brightness, contrast, etc.)
2. Use image generation for artistic transformations (styles, effects)
3. Let AI decide which approach based on request

**Implementation:**
```python
async def process_ai_manipulation(image_path, user_message, conversation_history):
    # Send image + message to vision model
    response = await openrouter_client.chat(
        model="google/gemini-3-flash-preview",
        messages=[
            *conversation_history,
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_message},
                    {"type": "image_url", "image_url": {"url": encode_image(image_path)}}
                ]
            }
        ]
    )
    
    # Parse response for operations
    ai_response = response.choices[0].message.content
    operations = extract_operations(ai_response)
    
    # Apply operations
    if operations['type'] == 'technical':
        result = apply_pillow_operations(image_path, operations['params'])
    elif operations['type'] == 'artistic':
        result = await generate_image_with_style(image_path, operations['style'])
    
    return result, ai_response
```

---

## 8. COST ESTIMATION

### Typical Usage Costs

**Background Removal (rembg):**
- Cost: $0.00 (local processing)
- Processing time: 1-3 seconds
- Quality: Excellent

**AI Chat - Gemini 3 Flash (Per Turn):**
- Image input: ~$0.0005 (1 image)
- Prompt: ~$0.0005 (1000 tokens)
- Completion: ~$0.003 (1000 tokens)
- **Total per turn: ~$0.004 ($0.004)**

**AI Chat - Claude Opus (Per Turn):**
- Image input: Included in prompt cost
- Prompt: ~$0.005 (1000 tokens)
- Completion: ~$0.025 (1000 tokens)
- **Total per turn: ~$0.03 ($0.03)**

**Estimated Monthly Costs (Personal Use):**
- 50 background removals: $0.00
- 100 AI chat turns (Gemini): $0.40
- Total: **~$0.50/month**

**Estimated Monthly Costs (Heavy Use):**
- 200 background removals: $0.00
- 500 AI chat turns (Gemini): $2.00
- Total: **~$2.00/month**

---

## 9. MODEL DISCOVERY API

### Get All Models
```
GET https://openrouter.ai/api/v1/models
```

**Response Structure:**
```json
{
  "data": [
    {
      "id": "google/gemini-3-flash-preview",
      "name": "Google: Gemini 3 Flash Preview",
      "description": "High speed, high value thinking model...",
      "context_length": 1048576,
      "architecture": {
        "modality": "text+image+file+audio+video->text",
        "input_modalities": ["text", "image", "file", "audio", "video"],
        "output_modalities": ["text"]
      },
      "pricing": {
        "prompt": "0.0000005",
        "completion": "0.000003",
        "image": "0.0000005"
      },
      "top_provider": {
        "max_completion_tokens": 65535
      }
    }
  ]
}
```

### Filter for Vision Models
Filter by: `input_modalities` contains "image"

### Implementation
```python
async def get_vision_models():
    response = requests.get("https://openrouter.ai/api/v1/models")
    all_models = response.json()['data']
    
    vision_models = [
        model for model in all_models
        if 'image' in model['architecture']['input_modalities']
    ]
    
    return vision_models
```

---

## 10. IMPLEMENTATION RECOMMENDATIONS

### Stage 3: AI Background Removal

**Technology Choice:** rembg (Python library)
- Install: `pip install rembg[gpu]` or `pip install rembg` (CPU)
- Model: u2net (default), u2net_human_seg, silueta, isnet-anime
- No API key required
- Runs locally

**Settings UI:**
- Show "AI Background Removal" as enabled by default
- No OAuth required for this feature
- Optional: Add Remove.bg as premium alternative

**Fallback Strategy:**
- Primary: rembg (free, local)
- Fallback: Offer Remove.bg API integration (paid)
- Settings toggle: "Use cloud-based removal (higher quality)"

### Stage 4: AI Image Manipulation Chat

**Default Model:** `google/gemini-3-flash-preview`

**Settings Configuration:**
```json
{
  "ai_chat_model": "google/gemini-3-flash-preview",
  "max_cost_per_request": 0.10,
  "enable_image_generation": false,
  "preferred_manipulation_method": "hybrid"
}
```

**Model Selector Features:**
- Search/filter by name, tags
- Display: name, description, tags, cost
- Show "Recommended" badge on default
- Allow favoriting models
- Show usage statistics

**Cost Tracking:**
- Display cost per message
- Show running total for conversation
- Warning at threshold ($0.10, configurable)
- Monthly usage report

---

## 11. API KEY MANAGEMENT

### Storage Security

**Encryption:**
```python
from cryptography.fernet import Fernet

def encrypt_api_key(api_key: str, encryption_key: bytes) -> str:
    f = Fernet(encryption_key)
    encrypted = f.encrypt(api_key.encode())
    return encrypted.decode()

def decrypt_api_key(encrypted_key: str, encryption_key: bytes) -> str:
    f = Fernet(encryption_key)
    decrypted = f.decrypt(encrypted_key.encode())
    return decrypted.decode()
```

**Database Storage:**
- Store encrypted in settings table
- Never log API keys
- Never return in API responses
- Use separate encryption key from database

**Environment Variable for Encryption Key:**
```bash
OPENROUTER_ENCRYPTION_KEY=<base64-encoded-32-byte-key>
```

---

## 12. ERROR HANDLING

### Common Errors

**Rate Limiting:**
```json
{
  "error": {
    "code": 429,
    "message": "Rate limit exceeded"
  }
}
```

**Invalid Model:**
```json
{
  "error": {
    "code": 404,
    "message": "Model not found"
  }
}
```

**Insufficient Credits:**
```json
{
  "error": {
    "code": 402,
    "message": "Insufficient credits"
  }
}
```

### Handling Strategy
1. Exponential backoff for rate limits
2. Model fallback for unavailable models
3. Clear user messaging for credit issues
4. Retry logic for transient failures

---

## CONCLUSION

### Key Findings

1. **OAuth2 PKCE** is well-documented and straightforward to implement
2. **Background Removal** best handled by rembg library (not OpenRouter)
3. **AI Chat** works excellently with Gemini 3 Flash Preview
4. **Cost** is very reasonable for personal use (~$0.50-2.00/month)
5. **Model Selection** should be user-configurable with smart defaults

### Implementation Path

**Stage 3:** 
- Use rembg for background removal (no OpenRouter needed)
- Implement OAuth2 PKCE for optional Remove.bg integration
- Build settings UI for AI configuration

**Stage 4:**
- Integrate Gemini 3 Flash Preview as default
- Build model selector with dynamic discovery
- Implement hybrid manipulation approach
- Add cost tracking and warnings

### Next Steps

1. Update IMPLEMENTATION_STRATEGY.md with these findings
2. Add rembg to Python requirements
3. Document OAuth2 flow in detail
4. Create model selection UI mockups
5. Begin Stage 1 implementation
