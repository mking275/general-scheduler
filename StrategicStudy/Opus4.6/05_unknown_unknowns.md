# Perspective 5: Unknown Unknowns — What Everyone Else Missed

**Research Date:** July 7, 2026
**Researcher Role:** Unknown Unknowns / Blind Spot Identification

---

## Executive Summary

This analysis identifies critical blind spots that conventional analyses miss. Key findings:

1. **ezyVet's Terms of Service explicitly prohibit browser automation and unsanctioned integrations.** The entire browser-automation leg may constitute a ToS violation.
2. **IDEXX's AI timeline is 12-18 months ahead of expectations.** ezyVet already shipped AI-Assisted SOAP Notes in 2025, has Patient Summarization in development, and DecisionIQ is live. New CEO Mike Erickson (May 2026) will accelerate AI.
3. **The veterinary AI scribe market is already crowded.** 8+ competitors shipping product.
4. **Regulatory complexity is underestimated.** AAVSB's March 2025 white paper establishes emerging informed-consent requirements.
5. **The liability architecture of a middleware layer creates novel legal exposure.**

**Bottom line:** The biggest risk isn't that the envelope fails technically — it's that it **succeeds just enough** to attract IDEXX's attention before VetAgent has sufficient switching costs.

---

## 1. Implicit Assumptions That Could Be Wrong

### Technical Assumptions
| # | Assumption | Why It Could Be Wrong | Severity |
|---|-----------|----------------------|----------|
| 1 | ezyVet's API will remain open | ToS already prohibit unsanctioned integrations | **Critical** |
| 2 | Browser automation is reliable fallback | ezyVet explicitly warns against automation tools | **Critical** |
| 3 | ezyVet's UI will remain stable | Cloud SaaS pushes updates without notice | **High** |
| 4 | API rate limits won't constrain real-time AI | Some endpoints limited to 1 req/min | **High** |
| 5 | We can write back reliably | Concurrent edits create conflicts | **High** |

### Business Assumptions
| # | Assumption | Why It Could Be Wrong | Severity |
|---|-----------|----------------------|----------|
| 6 | ezyVet won't ship AI fast enough | AI SOAP notes ALREADY live; Patient Summarization in dev | **Critical** |
| 7 | Practices want a layer between them and PIMS | Staff may prefer native features; "toggle tax" | **High** |
| 8 | 23-clinic pilot proves scalability | Single-ownership ≠ independent practice adoption | **Medium** |
| 9 | The envelope position is defensible | Platform companies routinely copy gap-fillers | **High** |
| 10 | IDEXX won't aggressively block | IDEXX/Epic parallel | **High** |

### Human Assumptions
| # | Assumption | Why It Could Be Wrong | Severity |
|---|-----------|----------------------|----------|
| 14 | Staff will adopt Vera as primary interface | ~15% active resistance; accuracy is #1 barrier | **Medium** |
| 15 | Vets will trust AI clinical recommendations | AAVSB warns against automation bias | **Medium** |
| 16 | Practice managers want less workflow control | Power users may resent abstraction | **Medium** |

---

## 2. What Domain Experts Would Tell Us

### A Veterinary Practice Manager:
> "You're underestimating how customized our ezyVet setup is. We spent 6 months configuring templates, picklists, workflows, permissions, and billing bundles. Every practice is essentially bespoke. And half our workarounds are sticky notes and text threads."

### An IDEXX Insider:
> "We're not sitting still. AI Notes shipped 2025. Patient Summarization is next. Our real moat isn't the software — it's 40 years of proprietary diagnostic data. DecisionIQ correlates lab results, imaging, and history in ways no third party can. August 2026 Investor Day will make this clear."

### A Healthcare IT Consultant:
> "I've watched this movie. Third parties build middleware on Epic, gain traction, then Epic copies, tightens API, or applies contract pressure. What happens when you're noticed but not essential? That's the kill zone."

### An RPA Architect:
> "The #1 cause of RPA death isn't technical failure — it's maintenance cost exceeding value. 70-75% of budgets consumed by maintenance. What does your system do when automation breaks at 2 AM and the practice opens at 7 AM?"

---

## 3. Veterinary-Specific Failure Modes

### 3.1 Species-Specific Clinical Complexity
- Vet medicine covers dogs, cats, horses, exotics, avians, reptiles, pocket pets, livestock
- Tylenol is safe for dogs but lethal for cats — AI must never confuse species context
- Drug dosages vary by species AND by weight

### 3.2 Controlled Substance Compliance
- DEA requires real-time logging with specific documentation
- EPCS certification required for electronic prescribing
- **If Vera touches prescription workflows, it enters a heavily regulated domain where errors have criminal consequences**

### 3.3 The VCPR Constraint
- Most states require in-person exam to establish VCPR before treatment
- AI-driven recommendations must operate WITHIN established VCPR
- Automated follow-ups that cross into "practicing veterinary medicine" put the practice's license at risk

### 3.4 Emotional Context in End-of-Life Care
- Euthanasia decisions and grief support are emotionally charged
- AI communications that feel impersonal during these moments destroy trust
- Automated follow-ups that reference a deceased pet incorrectly generate practice-threatening complaints

### 3.5 Emergency Triage Liability
- If Vera's risk scoring incorrectly downgrades an emergency, an animal dies
- AI triage creates a new liability nexus that malpractice insurance may not cover

---

## 4. Second-Order Effects

### If We Succeed: The Envelope Threat Goes Universal
- Every vertical SaaS vendor faces the same threat
- Incumbents preemptively tighten APIs — "API winter"
- IDEXX can point to VetAgent as the reason for restriction

### Fundraising Impact
- The narrative must evolve from "envelope ezyVet" to "AI operating system for veterinary practices"
- VCs will ask: "What happens when IDEXX turns off the API?"

---

## 5. Steel-Man Case AGAINST

*"The envelope strategy is a sophisticated version of building on quicksand:*

*You're optimizing for a closing window. IDEXX shipped AI SOAP notes in 2025. By the time you're at 100 clinics, ezyVet will have 80% of your features — free.*

*Your best-case is your worst-case. Success proves to IDEXX exactly what to build. You're doing free product research for a company with 100x your engineering resources.*

*The ToS problem isn't fixable. Browser automation violates ezyVet's terms. You can't build a business on prohibited activity.*

*Platform-dependent startups die. Zynga on Facebook. App developers on iOS. You're not different — you're just next.*

*The 'good enough' ceiling. When ezyVet's native AI is 60% as good but free, 90% of practices choose 'good enough.' This is the lesson from every bundling war."*

---

## 6. Questions for Dr. Goldsmith's Staff

### Front-Desk / Receptionists:
1. How many phone calls per day? What % are routine?
2. What info do you look up most in ezyVet? How long per lookup?
3. Do you use unofficial tools — spreadsheets, sticky notes, WhatsApp?
4. When ezyVet is down, what's your backup?
5. What's your biggest ezyVet frustration?

### Vet Techs:
6. How much time on documentation vs. patient care?
7. Walk through what happens after a consultation
8. Are there workflows where you work AROUND ezyVet?
9. How do you handle controlled substance logging?
10. If AI drafted your SOAPs, what would make you trust it?

### Practice Managers:
11. What reports do you pull regularly? What's missing?
12. How standardized are workflows across 23 locations?
13. What's your biggest data quality problem?
14. If AI sat between staff and ezyVet, what's your first concern?
15. How does IDEXX's diagnostics relationship influence tech choices?

### Shadow IT:
16. What workarounds have staff built that management doesn't know about?
17. Where does patient info live OUTSIDE ezyVet?
18. What tasks do staff routinely skip because ezyVet is too cumbersome?

---

## 7. The IDEXX Partnership Scenario

### Why IDEXX Might WANT Vera
1. Diagnostic utilization acceleration
2. Competitive positioning against Covetrus
3. Speed to market (partnership delivers in months vs. 2-3 years internal)
4. Burnout messaging alignment

### Possible Deal Structures
| Structure | IDEXX Interest | VetAgent Interest | Feasibility |
|-----------|---------------|-------------------|-------------|
| Revenue share (10-15%) | Low effort, some upside | Maintains independence | Medium |
| White-label (ezyVet AI Pro) | Full brand control | Guaranteed distribution | Medium-High |
| OEM licensing | Predictable cost | Stable revenue | Medium |
| Strategic investment (15-25% equity) | Alignment + option value | Capital, legitimacy, API access | **High** |
| Acquisition ($30-80M) | Full control | Exit for founders | Medium |

### Partnership Red Flags
- IDEXX using partnership for due diligence then building native
- Agreement restricting VetAgent from supporting other PIMS
- Revenue share tied to IDEXX's pricing decisions
- IP assignment requirements

---

## 8. The "Good Enough" Timeline

### IDEXX AI Features Already Shipped
| Date | Feature | Status |
|------|---------|--------|
| 2024 | inVue Dx AI pathology | Shipped |
| 2024 | DecisionIQ | Shipped |
| 2025 | ezyVet AI-Assisted Notes | Shipped |
| 2025 | AVA front-desk AI | Live integration |
| 2026 | Patient Summarization | In Development |
| 2026 Aug | Investor Day — AI strategy | Scheduled |

### How to Stay Ahead
1. Go deeper than note-taking — full workflow orchestration
2. Own the cross-PIMS story
3. Build proprietary clinical outcome data
4. Move to workflows IDEXX won't touch (comms, insurance, referrals)
5. Establish switching costs before IDEXX ships

---

## 9. Regulatory Blindspots

### FDA SaMD: Largely non-issue for veterinary software
### State Veterinary Practice Acts: THE real regulatory risk
- AAVSB March 2025 white paper: informed consent, transparency, oversight
- Licensed vet liable for AI errors regardless of tool
- State-by-state variation requires per-jurisdiction review

### Controlled Substances: Criminal liability territory
- Explicitly exclude from AI automation without EPCS certification

### Data Breach Liability as Middleware
- VetAgent needs: SOC 2 Type II, cyber insurance, incident response plan

---

## 10. The Human Element

### Adoption Curve Reality
```
Week 1-2:  Excitement (20% engaged)
Week 3-4:  First failures → skepticism (10%)
Week 5-8:  Core users see savings (35%)
Month 3:   Habit formation (50%)
Month 6:   Cultural integration OR abandonment
Month 12:  If still active, becomes essential (70%+)
```

**Critical period: Weeks 3-4.** First AI errors spread virally. A single embarrassing mistake sets adoption back months. Need a "first 30 days" playbook that prioritizes accuracy over comprehensiveness.

---

## Recommendations

### Immediate (30 Days)
1. **LEGAL REVIEW OF ezyVet ToS** — Existential risk
2. **Apply for ezyVet Integration Partner Program**
3. **Audit Vera's scope against controlled substance workflows**
4. **Prepare informed consent templates**

### Short-Term (60-90 Days)
5. Build cross-PIMS roadmap
6. Develop "first 30 days" adoption playbook
7. Engage IDEXX partnership exploratory before August Investor Day
8. Commission 50-state veterinary practice act review

### Medium-Term (6-12 Months)
9. Build proprietary clinical outcome dataset
10. Shift narrative to "AI operating system for veterinary practices"
11. Establish SOC 2 Type II certification
12. Develop species-specific AI models

---

## Open Questions

1. Has legal reviewed ezyVet's current ToS for browser automation prohibitions?
2. Does VetAgent have any formal agreement with ezyVet/IDEXX?
3. What happens to active sessions when ezyVet pushes a breaking UI update?
4. Has VetAgent explored IDEXX's Integration Partner Program?
5. What is Vera's accuracy rate on SOAP notes, stratified by species?
6. Does Vera touch controlled substance workflows?
7. Does VetAgent have cyber insurance covering middleware data breaches?
8. What's the plan when ezyVet ships Patient Summarization?
9. Is there a graceful degradation architecture when ezyVet integration fails?
10. What's our response plan for IDEXX's August 2026 Investor Day?

---

*Research completed July 2026.*
