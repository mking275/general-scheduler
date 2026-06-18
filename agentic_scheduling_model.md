# Meta-Analysis: Generalized Agentic Scheduling Data Model

## 1. Introduction
A synthesis of scheduling requirements across the 7 researched SMB niches reveals a common underlying structure. Whether dispatching an HVAC technician, booking a flight instructor, reserving an auto repair bay, or routing a freight carrier, the core problem is a multi-dimensional constraint satisfaction problem. 

In legacy systems, humans manually solve these constraints (the "calendar Tetris" problem). By breaking down the scheduling requirements into generalized first principles, we can design a single **Agentic Scheduling Engine** that can be adapted to any of these niches.

## 2. Generalized First Principles of Scheduling
1. **The Core Triad:** Every scheduling event requires a combination of **Task** (What), **Resource** (Who/With What), and **Time** (When).
2. **Multi-Dimensional Constraint Validation:**
   - *Skills/Certifications:* The human must be qualified (e.g., Part 141 CFI, HVAC Brazing Cert, Union Rules).
   - *Spatial/Locational:* Travel time between sites, routing optimization, or specific physical locations (Exam Room, Service Bay).
   - *Asset Availability:* Equipment must be functional and available (Planes not grounded for maintenance, AV inventory not double-booked).
3. **Agentic Mutability (The AI Edge):** A schedule is not static. It is a living puzzle that must be dynamically re-optimized when exceptions occur (e.g., emergency HVAC calls, delayed flights, broken rental equipment).

---

## 3. Generalized Data Model (Entities & Relationships)

To build a universal agentic scheduler, the architecture should be centered around these core entities:

### A. The Request (Intent)
An unstructured or structured demand for work or service from the customer.
- `Request_ID` (UUID)
- `Customer_ID` (Foreign Key)
- `Raw_Input` (Text, Audio, Email, RFP)
- `Parsed_Intent` (Classification: Emergency, Routine, Maintenance, Quote)
- `SLA_Deadline` (Timestamp for required completion)

### B. The Job (Work Order / Appointment)
The normalized event that needs to be scheduled. Created automatically by the Intake Agent parsing the Request.
- `Job_ID` (UUID)
- `Status` (Draft, Scheduled, In-Progress, Completed, Blocked)
- `Estimated_Duration` (Integer, minutes)
- `Location` (Geo-coordinates, Physical Address, Bay #, Room #)
- `Required_Skills` (Array of IDs: e.g., "Brazing Cert", "CFI")
- `Required_Assets` (Array of IDs: e.g., "Bucket Truck", "Ultrasound Machine")

### C. The Resource (Actors & Assets)
The entities fulfilling the Job. A Job requires one or more Resources.
- **Human Actor:**
  - `Actor_ID` (UUID)
  - `Type` (Vet, Mechanic, Pilot, Tech, Crew)
  - `Skills_Matrix` (Array of certifications/capabilities)
  - `Availability_Schedule` (Working hours, shifts, PTO)
- **Asset / Equipment / Location:**
  - `Asset_ID` (UUID)
  - `Type` (Vehicle, Bay, Plane, Rented Chair, Exam Room)
  - `Location` (Current state / GPS tracking)
  - `Status` (Available, In-Maintenance, Sub-rented, Grounded)

### D. The Time Block (Allocation)
The strict mapping of a Job to specific Resources over a specific period.
- `TimeBlock_ID` (UUID)
- `Job_ID` (Foreign Key)
- `Resource_IDs` (Array of Actors and Assets bound to this block)
- `Start_Time` (Timestamp)
- `End_Time` (Timestamp)
- `Travel_Buffer` (Pre/Post time needed for logistics/setup/teardown)

### E. The Agentic Layer (Policies & Rules)
Rules the AI uses to evaluate and mutate the schedule autonomously.
- `Conflict_Resolution_Strategy` (e.g., "Initiate Sub-rental", "Reschedule low-priority Job", "Alert human dispatcher")
- `Optimization_Metric` (Minimize travel time, maximize revenue, minimize overtime, strictly enforce maintenance intervals)

---

## 4. How the Generalized Model Maps to the Niches

| Niche | Request | Job / Time Block | Resources (Actors/Assets) | Core Constraints |
|---|---|---|---|---|
| **FBO / Flight School** | SMS/Email for plane | Flight Lesson | CFI + Aircraft | Part 141 Certs, Hobbs/Tach limits, Aircraft Maintenance |
| **Auto Repair** | Phone Call / Intake | Repair Order | Mechanic + Service Bay | Bay availability, Parts arrival time, Diagnostic skill |
| **HVAC / Field Service** | Emergency Call / Web | Dispatch / Work Order | Field Tech + Van | GPS Routing, EPA Certs, Emergency vs. Preventative |
| **Event Rental** | Emailed RFP | Event Logistics / Delivery | Crew + Delivery Truck + Inventory | Union Rules, Double-booking prevention, Travel Time |
| **Veterinary** | Intake Form / Call | Exam / Surgery | Vet + Exam Room + Equipment | Medical equipment availability, Room availability |
| **Freight Brokerage** | Email with BOL details | Freight Load | Carrier / Truck | FMCSA Authority, Weight limits, Pickup Windows |

*(Note: Photogrammetry relies heavily on compute-resource scheduling rather than human/asset physical scheduling, but the constraint-satisfaction model of Time + Resource [GPU] + Job [Render] still applies.)*

---

## 5. The "Agentic Workflow" Abstraction

In legacy software, users must manually bind `Request -> Job -> Resource -> TimeBlock` via rigid UIs. 

In our generalized architecture, we abstract the UI with three AI agents:
1. **The Intake Agent:** Listens to unformatted data (Emails, SMS, Voice), creates the `Request`, extracts parameters, and drafts the `Job`.
2. **The Constraints Engine (The Scheduler):** Queries `Resource` availability, calculates buffers (travel/maintenance), and creates a conflict-free `Time Block`.
3. **The Dispatch Agent:** Communicates the schedule to the Customer and Resources. If an exception occurs (e.g., a truck breaks down, an emergency job arrives), it autonomously reshuffles the board and notifies affected parties based on the `Agentic Layer` policies.
