import re
from typing import Any, Dict, List
class LocalVectorStore:
    def __init__(self, documents: List[Dict[str, Any]]): self.documents = documents
    def search(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        scored=[]
        for d in self.documents:
            words=set(re.findall(r"[a-z0-9]+", (d.get('title','')+' '+d.get('abstract','')+' '+d.get('content','')).lower()))
            score=len(terms & words)/max(1,len(terms|words))
            if score: scored.append((score,d))
        return [{**d, "similarity_score": round(s,4)} for s,d in sorted(scored,key=lambda x:x[0],reverse=True)[:k]]
