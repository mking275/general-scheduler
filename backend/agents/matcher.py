from typing import List, Tuple
from ..models import Job, Resource

class SemanticMatcher:
    def rank_resources(self, job: Job, candidate_resources: List[Resource]) -> List[Tuple[Resource, float]]:
        # MOCK VECTOR MATCHER for Prototype V1
        # In a real scenario, we compute cosine similarity between job.soft_requirements and resource.attributes
        # Here we just do a keyword match for demo purposes
        ranked = []
        for res in candidate_resources:
            score = 0.5 # Baseline
            if job.soft_requirements:
                if "dog" in job.soft_requirements.lower() and "dog" in res.attributes.lower():
                    score += 0.4
                if "bird" in job.soft_requirements.lower() and "bird" in res.attributes.lower():
                    score += 0.4
            ranked.append((res, score))
            
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
