"""
Access Control - Role-based document filtering
Enterprise-grade safety & security
"""
from typing import List, Dict, Optional, Set
from enum import Enum


class UserRole(Enum):
    """User roles for access control"""
    PUBLIC = "public"
    CUSTOMER = "customer"
    SUPPORT = "support"
    ADMIN = "admin"
    INTERNAL = "internal"


class AccessControl:
    """Manages access control and document filtering"""
    
    def __init__(self):
        """Initialize access control"""
        # Define document access levels
        self.document_access = {
            'public': {
                'scheme_overview': True,
                'factsheet_consolidated': True,
                'amfi': True,
                'sebi': True,
                'groww': True,
            },
            'restricted': {
                'sid_pdf': False,  # SID/KIM may contain sensitive details
                'kim_pdf': False,
            }
        }
        
        # Role-based access
        self.role_access = {
            UserRole.PUBLIC: {'public': True, 'restricted': False},
            UserRole.CUSTOMER: {'public': True, 'restricted': True},
            UserRole.SUPPORT: {'public': True, 'restricted': True},
            UserRole.ADMIN: {'public': True, 'restricted': True},
            UserRole.INTERNAL: {'public': True, 'restricted': True},
        }
    
    def filter_chunks_by_role(self, chunks: List[Dict], role: UserRole) -> List[Dict]:
        """
        Filter chunks based on user role
        
        Args:
            chunks: List of chunk dicts
            role: User role
            
        Returns:
            Filtered list of chunks
        """
        if role == UserRole.ADMIN or role == UserRole.INTERNAL:
            # Full access
            return chunks
        
        # Get access permissions for role
        access = self.role_access.get(role, self.role_access[UserRole.PUBLIC])
        
        filtered = []
        for chunk in chunks:
            source_id = chunk.get('source_id', '').lower()
            source_type = chunk.get('source_type', '').lower()
            
            # Check if source is restricted
            is_restricted = any(
                restricted_type in source_id or restricted_type in source_type
                for restricted_type in ['sid', 'kim']
            )
            
            # Allow if public or if role has restricted access
            if not is_restricted or access.get('restricted', False):
                filtered.append(chunk)
        
        return filtered
    
    def can_access_source(self, source_id: str, role: UserRole) -> bool:
        """
        Check if role can access a source
        
        Args:
            source_id: Source identifier
            role: User role
            
        Returns:
            True if access allowed
        """
        if role == UserRole.ADMIN or role == UserRole.INTERNAL:
            return True
        
        source_lower = source_id.lower()
        is_restricted = any(restricted in source_lower for restricted in ['sid', 'kim'])
        
        if not is_restricted:
            return True
        
        access = self.role_access.get(role, self.role_access[UserRole.PUBLIC])
        return access.get('restricted', False)
    
    def get_accessible_sources(self, role: UserRole) -> Set[str]:
        """
        Get list of accessible source types for a role
        
        Args:
            role: User role
            
        Returns:
            Set of accessible source types
        """
        access = self.role_access.get(role, self.role_access[UserRole.PUBLIC])
        
        accessible = set()
        for doc_type, is_public in self.document_access.get('public', {}).items():
            if is_public:
                accessible.add(doc_type)
        
        if access.get('restricted', False):
            for doc_type in self.document_access.get('restricted', {}).keys():
                accessible.add(doc_type)
        
        return accessible

