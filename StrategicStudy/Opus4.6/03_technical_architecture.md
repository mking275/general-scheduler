# VetAgent Envelope Orchestrator — Technical Architecture

**Perspective 3 of 6** | Strategic Study Series
**Date:** July 2026 | **Status:** Architecture Design
**Scope:** Technical architecture for wrapping Vera around ezyVet and other PIMS systems

---

## Executive Summary

VetAgent's "envelope strategy" positions Vera as an intelligent orchestration layer that wraps around existing veterinary PIMS systems — starting with ezyVet (IDEXX). This document defines the dual-mode technical architecture: **Mode A** (direct API integration via ezyVet's RESTful API) and **Mode B** (browser automation as an "APIless API" fallback). The architecture follows the Plaid playbook: prefer API when available, fall back to browser automation where APIs have gaps, and present a unified abstraction layer to Vera's agents regardless of underlying transport.

### Key Findings

1. **ezyVet's API is extensive but gated**: 200+ endpoints, OAuth 2.0 Client Credentials, 60 calls/min per endpoint (180 global/partner). Write access to clinical records requires Private API partnership with IDEXX.
2. **Critical API gaps exist**: No webhooks/event notifications, no real-time push. Clinical record writes restricted.
3. **Browser automation is viable but expensive**: Playwright recommended. Latency budget is 2-8 seconds per action — acceptable for background operations, not for real-time.
4. **HIPAA does not apply to veterinary**: But state veterinary practice acts and client PII protection laws demand HIPAA-like security.
5. **The adapter pattern is essential**: A `PIMSAdapter` abstraction provides Vera's agents with a stable interface regardless of transport.

---

## 1. Mode A: API Integration

### 1.1 ezyVet API Surface

| Attribute | Detail |
|---|---|
| **API Style** | RESTful, JSON |
| **Authentication** | OAuth 2.0 Client Credentials; Bearer tokens |
| **Token TTL** | 12 hours |
| **Rate Limits** | 60 calls/min per endpoint; 180 calls/min global per partner per database |
| **Endpoints** | 200+ documented |
| **Webhook Support** | ❌ No outbound webhooks — polling required |
| **Write Access** | Requires Private API Agreement |
| **Sandbox** | Available through partner onboarding |

### 1.2 Vera Capability → ezyVet API Mapping

| Vera Capability | Agent | API Endpoint(s) | Access Level | Gap Analysis |
|---|---|---|---|---|
| **SOAP Drafting** | `soap.py` | `POST /v2/clinicalrecord` | Private API (write) | ⚠️ Cannot write to locked records |
| **Intake Processing** | `intake.py` | `GET /v2/animal`, `GET /v2/contact` | Read (standard) | ✅ Read access available |
| **Risk Scoring** | `risk.py` | `GET /v2/clinicalrecord`, `GET /v2/diagnostic` | Read (standard) | ✅ Can pull clinical history |
| **Follow-ups** | `followup.py` | `POST /v2/communicationtask` | Private API (write) | ⚠️ Requires specific endpoint access |
| **Waitlist** | `waitlist.py` | `GET/PUT /v2/appointment` | Private API (write) | ❌ No dedicated waitlist API |
| **Prescriptions** | `prescriptions.py` | `POST /v2/prescription` | Private API (write) | ⚠️ Tightly coupled with dispensing |
| **Care Protocols** | `preventive_care.py` | `GET /v2/standardofcare` | Read (standard) | ✅ SOC system readable |
| **Appointments** | `booking_agent.py` | `GET/POST /v2/appointment` | Standard/Private | ⚠️ Create may require partnership |

### 1.3 Rate Limit Strategy

| Priority | Use Case | Allocation | Calls/Min |
|---|---|---|---|
| P0 | Real-Time user-triggered reads | 20% | 36 |
| P1 | Clinical writes (SOAP, Rx, labs) | 40% | 72 |
| P2 | Background sync, cache refresh | 30% | 54 |
| P3 | Reporting, data aggregation | 10% | 18 |
| **Total** | | **100%** | **180** |

### 1.4 Data Residency: Cache vs Live

| Data Type | Strategy | TTL |
|---|---|---|
| Patient demographics | Read-through cache | 5 min |
| Appointments (today) | Live read | 0 |
| Clinical records | Read-through cache | 1 min |
| SOC protocols | Periodic sync | 24 hours |
| Products/inventory | Periodic sync | 1 hour |
| Invoices | Live read | 0 |

---

## 2. Mode B: 'APIless API' — Browser Automation

### 2.1 Framework Selection: Playwright

| Framework | Verdict | Reasoning |
|---|---|---|
| **Playwright** ✅ | **Recommended** | Python-native, auto-waiting, browser contexts, built-in stealth, multi-browser |
| Puppeteer | No | JS-only, Chrome-only |
| CDP Direct | No | Too low-level |
| Selenium | No | Legacy, slower |

### 2.2 Authentication & Session Management

| Scenario | Approach |
|---|---|
| No 2FA | Standard username/password automation |
| TOTP | Store TOTP seed; generate codes programmatically |
| SMS 2FA | ❌ Cannot automate — require app-based 2FA |
| SSO/SAML | Requires separate IdP automation |
| CAPTCHA | ❌ Hard block. Fall back to Mode A or manual. |

### 2.3 Latency Budget

| Operation | Target | Achievable? |
|---|---|---|
| Read patient record | 1-3 sec | ✅ |
| Write SOAP note | 3-8 sec | ⚠️ |
| Create appointment | 2-5 sec | ⚠️ |
| Generate invoice | 5-10 sec | ⚠️ |
| Bulk data sync | 30-120 sec | ✅ |

### 2.4 Selector Healing Strategy
1. **Primary**: `data-testid` or `aria-label` attributes
2. **Secondary**: CSS class + structure-based selectors
3. **Tertiary**: XPath with text content matching
4. **Emergency**: Network interception — capture ezyVet's internal API calls

### 2.5 Compute Architecture: Hybrid

- Active clinics: warm browser context pool (1 per clinic)
- Idle clinics: no browser — cold start in ~5s
- Peak hours: scale pool up
- Off hours: scale to 0

**Cost:** Active clinic ~$15-25/mo (Browserbase) or ~$5-10/mo (self-hosted)

---

## 3. Orchestration Layer

### 3.1 Operation Routing Table

| Operation | Preferred Mode | Fallback |
|---|---|---|
| `readPatient()` | API | Browser |
| `readAppointments()` | API | Browser |
| `writeSOAP()` | API (if partnership) | Browser |
| `createAppointment()` | API (if partnership) | Browser |
| `createInvoice()` | API (if partnership) | Browser |
| `manageWaitlist()` | Browser | None |
| `fillIntakeForm()` | Browser | None |
| `readLabResults()` | API | Browser |
| `syncPatientData()` | API | Browser |

### 3.2 Common Abstraction Layer: PIMSAdapter

```python
from abc import ABC, abstractmethod

class PIMSAdapter(ABC):
    """Universal PIMS interface. Each PIMS system implements this."""
    
    @abstractmethod
    async def read_patient(self, patient_id: str) -> PatientRecord: ...
    
    @abstractmethod
    async def write_soap(self, patient_id: str, soap: SOAPNote) -> str: ...
    
    @abstractmethod
    async def read_appointments(self, date: str, clinic_id: str) -> List[Appointment]: ...
    
    @abstractmethod
    async def create_appointment(self, appt: AppointmentCreate) -> str: ...
    
    @abstractmethod
    async def create_invoice(self, invoice: InvoiceCreate) -> str: ...
    
    @abstractmethod
    async def create_prescription(self, rx: PrescriptionCreate) -> str: ...
    
    @abstractmethod
    async def health_check(self) -> PIMSHealthStatus: ...


class EzyVetHybridAdapter(PIMSAdapter):
    """Production adapter: Routes to API or Browser with fallback."""
    
    def __init__(self, api: EzyVetAPIAdapter, browser: EzyVetBrowserAdapter):
        self.api = api
        self.browser = browser
    
    async def write_soap(self, patient_id: str, soap: SOAPNote) -> str:
        try:
            return await self.api.write_soap(patient_id, soap)
        except (APIWriteNotAvailable, RateLimitExceeded):
            return await self.browser.write_soap(patient_id, soap)
```

Future adapters: `CornerstoneAdapter`, `ProvetCloudAdapter`, etc.

---

## 4. Data Architecture

### 4.1 Source of Truth Rules

| Data Type | Source of Truth | Vera's Role | Conflict Rule |
|---|---|---|---|
| Patient demographics | ezyVet | Read-only cache | ezyVet always wins |
| Appointment schedule | ezyVet | Read + create | ezyVet always wins |
| SOAP notes | ezyVet (after write-back) | Draft → push | Vet's edits override Vera |
| Risk scores | Vera (exclusively) | Owner | Not in ezyVet; no conflict |
| Waitlist | Vera (exclusively) | Owner | Vera is sole source |
| Intake forms | Vera (exclusively) | Owner | Pushed to ezyVet on completion |
| Invoices/billing | ezyVet | Read-only | ezyVet always wins |

### 4.2 Conflict Resolution
1. **Write-then-verify**: After every write, read back and compare
2. **Short cache TTLs**: 1-5 min to minimize staleness
3. **Optimistic approach**: ezyVet doesn't support version fields
4. **Staff wins rule**: Staff modifications take priority

### 4.3 Privacy & Regulatory

| Requirement | Source | Implementation |
|---|---|---|
| Client PII protection | State data breach laws | AES-256 at rest; TLS in transit |
| Veterinary record confidentiality | State Practice Acts | Per-clinic data isolation |
| ezyVet contractual requirements | IDEXX Partner Agreement | No unauthorized third-party access |
| Payment data (PCI-DSS) | Card network rules | Stripe/Square handles card data |

---

## 5. Key Risks

| # | Risk | Severity | Probability | Mitigation |
|---|---|---|---|---|
| R1 | IDEXX blocks API access | 🔴 Critical | Medium | Mode B fallback; pursue partnership |
| R2 | ezyVet adds anti-bot detection | 🔴 Critical | Medium | Stealth plugins; maintain API as primary |
| R3 | ezyVet DOM changes break Mode B | 🟡 High | High | Selector healing; network interception; weekly regression tests |
| R4 | Rate limits insufficient | 🟡 High | Medium | Aggressive caching; priority-based budgeting |
| R5 | ezyVet ToS violation | 🔴 Critical | High | **Legal review required.** |
| R6 | Data integrity risk | 🟡 High | Medium | Write-then-verify; comprehensive validation |

---

## 6. Recommendations

### Phase 1: Foundation (Months 1-3)
1. Apply for ezyVet API Partnership immediately
2. Build `PIMSAdapter` abstraction layer first
3. Implement Mode A (API) for all read operations
4. Build browser automation infrastructure (Mode B) in parallel

### Phase 2: Write Path (Months 3-6)
5. If partnership approved: implement API writes; Mode B becomes fallback
6. If partnership denied: Mode B becomes primary write path
7. Build polling-based sync engine with `modified_at` cursors
8. Implement conflict resolution (write-then-verify)

### Phase 3: Scale (Months 6-12)
9. Add adapters for Cornerstone, ProVet Cloud
10. Move to managed browser infrastructure
11. Build contract testing for API schema drift

> [!WARNING]
> **The biggest strategic decision is whether to pursue ezyVet/IDEXX partnership or operate 'around' them.** Pursue partnership aggressively while building Mode B as insurance. The Plaid analogy: start with scraping, get banks to cooperate.

---

## 7. Open Questions

1. Will IDEXX approve VetAgent as an API partner?
2. Does ezyVet use Cloudflare that would block cloud-IP browser automation?
3. What is the legal exposure of Mode B under ezyVet's ToS?
4. Should Vera's risk scores be pushed back into ezyVet?
5. Can we use ezyVet's Data Lake for reads instead of API polling?
6. How do clinics feel about giving Vera a staff login for browser automation?
7. What state veterinary practice acts affect data handling?

---

*End of Technical Architecture — Perspective 3*
