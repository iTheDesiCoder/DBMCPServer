from rapidfuzz import process, fuzz
from typing import List, Dict, Tuple, Optional, Any
from app.config import settings
from app.models import DatabaseObjectType, MetadataSuggestion
import logging

logger = logging.getLogger(__name__)


class FuzzyMatcher:
    def __init__(self):
        self.threshold = settings.fuzzy_threshold
        self.max_suggestions = settings.max_suggestions
        self.alias_mappings: Dict[str, str] = {}
        
    def add_alias_mapping(self, alias: str, actual_name: str):
        """Add custom alias mapping"""
        self.alias_mappings[alias.lower()] = actual_name
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query string for better matching"""
        query = query.lower().strip()
        
        # Check if there's a direct alias mapping
        if query in self.alias_mappings:
            return self.alias_mappings[query]
            
        # Remove common prefixes/suffixes
        prefixes = ['sp_', 'fn_', 'vw_', 'tbl_']
        suffixes = ['_sp', '_fn', '_vw', '_tbl']
        
        original_query = query
        for prefix in prefixes:
            if query.startswith(prefix):
                query = query[len(prefix):]
                break
                
        for suffix in suffixes:
            if query.endswith(suffix):
                query = query[:-len(suffix)]
                break
        
        return query
      def _calculate_weighted_score(self, query: str, candidate: Dict[str, Any]) -> float:
        """Calculate weighted similarity score"""
        name = candidate.get('name', '')
        obj_type = candidate.get('type', '')
        schema = candidate.get('schema', candidate.get('schema_name', ''))
        
        # Base similarity score
        base_score = fuzz.ratio(query.lower(), name.lower())
        
        # Bonus for exact matches or starts with
        if name.lower().startswith(query.lower()):
            base_score += 20
        elif query.lower() in name.lower():
            base_score += 10
            
        # Type-based scoring adjustments
        type_weights = {
            DatabaseObjectType.STORED_PROCEDURE: 1.2,
            DatabaseObjectType.FUNCTION: 1.1,
            DatabaseObjectType.TABLE: 1.0,
            DatabaseObjectType.VIEW: 0.9
        }
        
        weight = type_weights.get(obj_type, 1.0)
        weighted_score = base_score * weight
        
        # Schema preference (dbo gets slight boost)
        if schema.lower() == 'dbo':
            weighted_score += 5
            
        return min(weighted_score, 100.0)  # Cap at 100
    
    def find_best_matches(self, query: str, candidates: List[Dict[str, Any]]) -> List[MetadataSuggestion]:
        """Find best matching database objects"""
        if not query or not candidates:
            return []
            
        normalized_query = self._normalize_query(query)
        
        # Calculate scores for all candidates
        scored_candidates = []
        for candidate in candidates:
            score = self._calculate_weighted_score(normalized_query, candidate)
            if score >= self.threshold:
                scored_candidates.append((score, candidate))
        
        # Sort by score (descending) and take top matches
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_matches = scored_candidates[:self.max_suggestions]
        
        # Convert to MetadataSuggestion objects        suggestions = []
        for score, candidate in top_matches:
            try:
                suggestion = MetadataSuggestion(
                    type=candidate.get('type', DatabaseObjectType.TABLE),
                    name=candidate.get('name', ''),
                    schema_name=candidate.get('schema', candidate.get('schema_name', '')),
                    score=score / 100.0,  # Normalize to 0-1
                    params=candidate.get('params', []),
                    returns=candidate.get('returns', []),
                    related_tables=candidate.get('related_tables', []),
                    description=candidate.get('description')
                )
                suggestions.append(suggestion)
            except Exception as e:
                logger.error(f"Error creating suggestion for candidate {candidate}: {e}")
                continue
                
        return suggestions
    
    def fuzzy_search_simple(self, query: str, candidates: List[str]) -> List[Tuple[str, float]]:
        """Simple fuzzy search for string lists"""
        if not query or not candidates:
            return []
            
        results = process.extract(
            query, 
            candidates, 
            scorer=fuzz.ratio,
            limit=self.max_suggestions
        )
        
        # Filter by threshold and return with normalized scores
        filtered_results = [
            (match, score / 100.0) 
            for match, score, _ in results 
            if score >= self.threshold
        ]
        
        return filtered_results


# Global fuzzy matcher instance
fuzzy_matcher = FuzzyMatcher()
