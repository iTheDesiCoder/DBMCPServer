from rapidfuzz import process, fuzz
from typing import List, Dict, Tuple, Optional, Any
from app.config import settings
from app.models import DatabaseObjectType, MetadataSuggestion
import logging

logger = logging.getLogger(__name__)


class FuzzyMatcher:
    def __init__(self):
        self.threshold = getattr(settings, 'fuzzy_threshold', 60)  # Default 60% similarity
        self.max_suggestions = getattr(settings, 'max_suggestions', 10)  # Default 10 suggestions
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
        prefixes = ['sp_', 'fn_', 'vw_', 'tbl_', 'usp_', 'ufn_']
        suffixes = ['_sp', '_fn', '_vw', '_tbl', '_proc', '_func']
        
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
        if name.lower() == query.lower():
            base_score = 100  # Perfect match
        elif name.lower().startswith(query.lower()):
            base_score += 20
        elif query.lower() in name.lower():
            base_score += 10
            
        # Additional scoring for partial word matches
        query_words = query.lower().split('_')
        name_words = name.lower().split('_')
        
        word_matches = sum(1 for qword in query_words if any(qword in nword for nword in name_words))
        if word_matches > 0:
            base_score += (word_matches / len(query_words)) * 15
            
        # Type-based scoring adjustments
        type_weights = {
            'STORED_PROCEDURE': 1.2,
            'stored_procedure': 1.2,
            'PROCEDURE': 1.2,
            'procedure': 1.2,
            'FUNCTION': 1.1,
            'function': 1.1,
            'TABLE': 1.0,
            'table': 1.0,
            'VIEW': 0.9,
            'view': 0.9
        }
        
        weight = type_weights.get(obj_type, 1.0)
        weighted_score = base_score * weight
        
        # Schema preference (dbo gets slight boost)
        if schema and schema.lower() == 'dbo':
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
        
        # Convert to MetadataSuggestion objects
        suggestions = []
        for score, candidate in top_matches:
            try:
                # Handle different object type formats
                obj_type = candidate.get('type', 'table')
                if isinstance(obj_type, str):
                    if obj_type.lower() in ['stored_procedure', 'procedure']:
                        obj_type = DatabaseObjectType.STORED_PROCEDURE
                    elif obj_type.lower() == 'function':
                        obj_type = DatabaseObjectType.FUNCTION
                    elif obj_type.lower() == 'view':
                        obj_type = DatabaseObjectType.VIEW
                    else:
                        obj_type = DatabaseObjectType.TABLE
                
                suggestion = MetadataSuggestion(
                    type=obj_type,
                    name=candidate.get('name', ''),
                    schema_name=candidate.get('schema', candidate.get('schema_name', '')),
                    score=score / 100.0,  # Normalize to 0-1
                    params=candidate.get('params', candidate.get('parameters', [])),
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
            
        # Normalize query
        normalized_query = self._normalize_query(query)
        
        results = process.extract(
            normalized_query, 
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
        
    def rank_search_results(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank existing search results using fuzzy matching"""
        if not query or not results:
            return results
            
        # Add fuzzy scores to results
        scored_results = []
        for result in results:
            score = self._calculate_weighted_score(query, result)
            result_copy = result.copy()
            result_copy['fuzzy_score'] = score
            scored_results.append(result_copy)
        
        # Sort by fuzzy score (descending)
        scored_results.sort(key=lambda x: x.get('fuzzy_score', 0), reverse=True)
        
        return scored_results


# Global fuzzy matcher instance
fuzzy_matcher = FuzzyMatcher()


# Convenience functions
def find_best_matches(query: str, candidates: List[Dict[str, Any]]) -> List[MetadataSuggestion]:
    """Convenience function for finding best matches"""
    return fuzzy_matcher.find_best_matches(query, candidates)


def fuzzy_search(query: str, candidates: List[str]) -> List[Tuple[str, float]]:
    """Convenience function for simple fuzzy search"""
    return fuzzy_matcher.fuzzy_search_simple(query, candidates)


def rank_results(query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convenience function for ranking search results"""
    return fuzzy_matcher.rank_search_results(query, results)


def add_alias(alias: str, actual_name: str):
    """Add a custom alias mapping"""
    fuzzy_matcher.add_alias_mapping(alias, actual_name)
