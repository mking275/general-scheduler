# Data Model: General Scheduler

## Entities

### Job
- `id`: string (UUID)
- `required_skills`: string[] (e.g., ["Surgery"])
- `estimated_duration`: integer (minutes)
- `soft_requirements`: string (natural language context)

### Resource
- `id`: string (UUID)
- `type`: enum ("Vet", "Room", "Equipment")
- `name`: string
- `hard_skills`: string[]
- `attributes`: string (natural language attributes for vector search)
- `availability_windows`: TimeRange[]

### TimeBlock
- `id`: string (UUID)
- `job_id`: string (FK -> Job.id)
- `resource_ids`: string[] (FK -> Resource.id)
- `start_time`: datetime
- `end_time`: datetime
