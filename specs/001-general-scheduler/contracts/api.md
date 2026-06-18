# Interface Contracts: Scheduling API

## POST /api/schedule
**Description:** Intake endpoint for unstructured natural language scheduling requests.

**Request Body:**
```json
{
  "request_id": "req_123",
  "text": "Book an emergency surgery for a Golden Retriever at 2pm"
}
```

**Response (Success):**
```json
{
  "status": "success",
  "timeblock_id": "tb_456",
  "job": { "required_skills": ["Surgery"], "estimated_duration": 60 },
  "resources": [
    { "id": "vet_1", "name": "Dr. Smith" },
    { "id": "room_1", "name": "Operating Room A" }
  ],
  "start_time": "2026-06-18T14:00:00Z",
  "end_time": "2026-06-18T15:00:00Z",
  "verbose_log": [
    "INTAKE: Parsed request into Job[Surgery, 60m]",
    "MATCH: Ranked Dr. Smith (98%) and Dr. Jones (85%)",
    "SOLVE: Dr. Smith available. Room A available.",
    "DISPATCH: Confirmed."
  ]
}
```
