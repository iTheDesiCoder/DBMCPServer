"""
Services module for database metadata operations
"""
from app.services.metadata import metadata_service
from app.services.fuzzy_match import fuzzy_matcher

# Export the main service instance
__all__ = ['metadata_service', 'fuzzy_matcher']
