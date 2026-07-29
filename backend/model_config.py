"""Model identities — ONE place, so they cannot drift apart again.

Scattered literals are why `gemini-2.5-flash` (a retired family) survived in three
call sites after the fleet moved to gen-3. Import from here; never inline a model
string.

**Endpoint coupling — read before switching to Vertex.** Gen-3 models serve only
from the `global` endpoint. On the *Vertex* path (`genai.Client(vertexai=True,
project=…, location=…)`) the model name and the client location must move
TOGETHER — `us-central1` is stuck on the 2.5 family and a gen-3 model there
404s. The call sites here use the *Developer API* path (`genai.Client(api_key=…)`),
which has no location parameter and is unaffected; the constraint applies the
moment anything moves to Vertex.
"""

# Text / reasoning tier — drafting, chat, summarization.
GEMINI_FLASH = "gemini-3.5-flash"

# Deeper inference tier — reserve for work that earns the cost.
GEMINI_PRO = "gemini-3.1-pro-preview"

# Realtime speech-to-speech (voice bridge). Distinct family; do not substitute
# the text-tier model here.
GEMINI_LIVE = "gemini-3.1-flash-live-preview"

# Set when running against Vertex rather than the Developer API. Gen-3 requires
# this exact value; see the endpoint-coupling note above.
VERTEX_LOCATION = "global"

# ── KNOWN DRIFT: these constants bind MODELS; the fleet binds TASK CLASSES ────
# Corrected 2026-07-29. The platform runtime policy is task-class based:
#   onboarding-converse (default) -> PREMIUM  -> claude-opus-4-8 (anthropic-direct,
#                                                falling back to Claude-on-Vertex,
#                                                then Gemini)
#   extract                       -> STANDARD -> gemini-3.5-flash
# i.e. Claude is the CONVERSATIONAL brain and Gemini the EXTRACTION brain — the
# opposite of what a reader would infer from this file today.
#
# VetAgent's voice path correctly stays Gemini Live (latency; no Claude realtime
# equivalent). But the non-voice conversational sites that import GEMINI_FLASH
# (main.py Vera chat, agents/soap.py, agents/followup.py) are drafting/conversing
# on the EXTRACTION tier, which drifts from the fleet pattern.
#
# The fix is structural, not a string swap: express task_class -> tier -> model as
# POLICY (COS-004 shape) so a tier decision — e.g. spec-012's SOAP drafting — is a
# binding change, never a code change. Tracked, not yet done; do not "fix" it by
# swapping these literals to a Claude id, which would hardcode the same mistake in
# the other direction and add a serving path with no policy behind it.
