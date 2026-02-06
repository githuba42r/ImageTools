# AI Research & Implementation Update Summary

**Date:** February 6, 2026  
**Status:** Research Complete

---

## RESEARCH COMPLETED

I have completed comprehensive research on OpenRouter.ai API capabilities and updated the implementation strategy with detailed findings.

### Documents Created

1. **AI_RESEARCH_FINDINGS.md** (18KB)
   - Complete research documentation
   - OAuth2 PKCE implementation details
   - Model recommendations with pricing
   - Code examples and best practices

2. **IMPLEMENTATION_STRATEGY.md** (68KB - Updated)
   - Added Appendix A with research findings
   - Updated Stage 3 and Stage 4 specifications
   - Revised technology stack and dependencies
   - Updated environment variables

---

## KEY FINDINGS

### 1. OAuth2 PKCE Implementation
✓ Well-documented three-step flow
✓ SHA-256 code challenge method (S256)
✓ Secure user-controlled API key enrollment
✓ Implementation examples for frontend and backend

### 2. Background Removal (Stage 3)

**IMPORTANT DECISION:**
- **DO NOT use OpenRouter for background removal**
- **USE rembg Python library instead**

**Rationale:**
- rembg is FREE (no API costs)
- Better quality (specialized segmentation models)
- Faster (1-3 seconds, local processing)
- No rate limits
- No internet dependency

**Impact on Stage 3:**
- Still implement OAuth2 PKCE (needed for Stage 4)
- Background removal doesn't require OpenRouter
- Can add Remove.bg API as premium alternative later

### 3. AI Image Manipulation Chat (Stage 4)

**Recommended Model:** Google Gemini 3 Flash Preview

**Model ID:** `google/gemini-3-flash-preview`

**Key Features:**
- Vision: Excellent image understanding
- Context: 1M tokens
- Speed: Fast inference
- Multimodal: text, image, audio, video, PDF input
- Reasoning: Configurable levels

**Pricing:**
- ~$0.004 per conversation turn
- ~$0.20-2.00 per month for personal use
- Very affordable!

**Why This Model:**
- Best balance of cost, speed, and quality
- Excellent at understanding image manipulation requests
- Strong multi-turn conversation
- Low latency for interactive chat

**Alternative Models Researched:**
- Claude Opus 4.6 (premium option, $0.03/turn)
- Gemini 2.5 Flash (budget option, $0.001/turn)
- Mistral Pixtral Large (open source, $0.005/turn)

---

## IMPLEMENTATION CHANGES

### Stage 3: AI Background Removal (3-4 days)

**Technology Stack:**
```
Primary: rembg Python library
Models: u2net, u2net_human_seg, isnet-general-use
Optional: Remove.bg API (premium feature)
```

**New Dependencies:**
```bash
pip install rembg[gpu]  # GPU version
pip install rembg       # CPU version
```

**Still Implementing:**
- OAuth2 PKCE flow (for Stage 4)
- Settings UI with AI configuration
- Model selection for rembg

**Cost:** $0.00 per image (local processing)

### Stage 4: AI Image Manipulation Chat (5-6 days)

**Technology Stack:**
```
API: OpenRouter.ai
Default Model: google/gemini-3-flash-preview
Approach: Hybrid (text instructions + local Pillow processing)
```

**Features:**
- Dynamic model discovery
- Model selector with search/filter
- Cost tracking per message
- Conversation history
- Multi-turn dialogue
- Hybrid manipulation (AI instructions + local edits)

**Cost:** ~$0.004 per turn, ~$0.20-2.00/month personal use

---

## UPDATED TIMELINE

**Original:** 24-35 days  
**Revised:** 23-32 days (slightly faster due to rembg simplification)

**Breakdown:**
- Stage 1 (Core MVP): 10-14 days
- Stage 2 (Image Editor): 4-6 days
- Stage 3 (Background Removal): 3-4 days (reduced from 3-5)
- Stage 4 (AI Chat): 5-6 days (reduced from 5-7)

---

## COST ANALYSIS

### Background Removal
- rembg (local): **$0.00 per image**
- Remove.bg API: ~$0.20 per image (optional premium)

### AI Chat (Gemini 3 Flash)
- Per message turn: **$0.004**
- 50 turns/month: **$0.20**
- 150 turns/month: **$0.60**
- 500 turns/month: **$2.00**

### Total Estimated Monthly Cost
- Light use: **$0.20/month**
- Moderate use: **$0.60/month**
- Heavy use: **$2.00/month**

This is extremely affordable for personal use!

---

## TECHNICAL HIGHLIGHTS

### OAuth2 PKCE Flow
```javascript
// 1. Generate PKCE pair
const verifier = generateRandomString(128);
const challenge = await sha256(verifier);

// 2. Redirect to OpenRouter
window.location = `https://openrouter.ai/auth?callback_url=${url}&code_challenge=${challenge}&code_challenge_method=S256`;

// 3. Exchange code for API key
const response = await fetch('https://openrouter.ai/api/v1/auth/keys', {
  method: 'POST',
  body: JSON.stringify({ code, code_verifier: verifier, code_challenge_method: 'S256' })
});
const { key } = await response.json();
```

### Background Removal
```python
from rembg import remove
from PIL import Image

# One line to remove background!
output = remove(Image.open(input_path))
output.save(output_path, 'PNG')
```

### AI Chat
```python
response = await openrouter.chat(
    model="google/gemini-3-flash-preview",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Make this warmer"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
            ]
        }
    ]
)
```

---

## SECURITY MEASURES

### API Key Storage
- Encrypt with Fernet (cryptography library)
- Store encrypted in SQLite
- Never log API keys
- Separate encryption key (environment variable)

### OAuth Security
- SHA-256 code challenge (S256 method)
- CSRF protection on callback
- HTTPS only
- Session storage for code verifier
- Validate redirect URLs

---

## UPDATED DEPENDENCIES

### Python (backend/requirements.txt)
```txt
# Existing
fastapi==0.110.0
pillow==10.2.0
sqlalchemy==2.0.27
# ... others

# NEW for AI features
rembg==2.0.50
onnxruntime-gpu==1.16.3  # or onnxruntime for CPU
openai==1.12.0           # OpenRouter compatible
httpx==0.26.0
tiktoken==0.5.2
cryptography==42.0.0
```

### Frontend (no changes)
- OAuth2 PKCE uses native Web Crypto API
- No additional packages needed

---

## ENVIRONMENT VARIABLES ADDED

```bash
# OpenRouter API
OPENROUTER_API_URL=https://openrouter.ai/api/v1
OPENROUTER_OAUTH_CALLBACK_URL=http://localhost:8000/app/oauth/callback
OPENROUTER_ENCRYPTION_KEY=<generate-with-Fernet>

# Background Removal
BACKGROUND_REMOVAL_METHOD=rembg
REMBG_MODEL=u2net
ENABLE_GPU_ACCELERATION=false

# AI Chat
DEFAULT_AI_CHAT_MODEL=google/gemini-3-flash-preview
MAX_COST_PER_REQUEST=0.10
MONTHLY_COST_LIMIT=10.00
ENABLE_COST_TRACKING=true
```

---

## NEXT STEPS

### For Your Review:
1. ✓ Review AI_RESEARCH_FINDINGS.md for complete details
2. ✓ Review IMPLEMENTATION_STRATEGY.md (Appendix A)
3. ✓ Approve technology choices:
   - rembg for background removal
   - Gemini 3 Flash for AI chat
4. ✓ Approve revised timeline (23-32 days)
5. ✓ Approve cost estimates

### Ready to Start:
Once approved, we can begin Stage 1 implementation immediately:
- Backend setup (FastAPI, SQLAlchemy, config)
- Database models
- Session management
- Chunked upload system
- Compression engine
- Frontend setup (Vue 3, Vite, Tailwind)

---

## QUESTIONS?

Let me know if you need:
- More details on any aspect
- Alternative model recommendations
- Cost optimization strategies
- Implementation clarifications
- Timeline adjustments

I'm ready to begin implementation when you approve the plan!

---

**Status:** ✓ Research Complete | ⏸ Awaiting Approval | ⏭ Ready for Stage 1
