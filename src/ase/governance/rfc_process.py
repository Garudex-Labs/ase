"""
RFC (Request for Comments) Process Specification

This module defines the RFC proposal, review, and approval procedures
for ASE protocol changes, including proof-of-concept requirements.

Validates: Requirements 10.1, 10.4
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from pydantic import Field
from ase.core.serialization import SerializableModel


class RFCStatus(Enum):
    """RFC proposal status lifecycle."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    POC_REQUIRED = "poc_required"
    POC_IN_PROGRESS = "poc_in_progress"
    POC_COMPLETED = "poc_completed"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    IMPLEMENTED = "implemented"


class RFCCategory(Enum):
    """RFC proposal categories."""
    PROTOCOL_EXTENSION = "protocol_extension"
    SCHEMA_CHANGE = "schema_change"
    SECURITY_ENHANCEMENT = "security_enhancement"
    PERFORMANCE_IMPROVEMENT = "performance_improvement"
    BACKWARD_COMPATIBILITY = "backward_compatibility"
    GOVERNANCE_PROCESS = "governance_process"
    DOCUMENTATION = "documentation"


class ProofOfConceptRequirement(SerializableModel):
    """
    Proof-of-concept requirement for RFC proposals.
    """
    required: bool
    description: str
    acceptance_criteria: List[str] = Field(..., alias="acceptanceCriteria")
    implementation_language: Optional[str] = Field(None, alias="implementationLanguage")
    repository_url: Optional[str] = Field(None, alias="repositoryUrl")
    demo_url: Optional[str] = Field(None, alias="demoUrl")
    test_results_url: Optional[str] = Field(None, alias="testResultsUrl")
    completed: bool = False
    completion_date: Optional[datetime] = Field(None, alias="completionDate")
    reviewer_notes: Optional[str] = Field(None, alias="reviewerNotes")
    
    def validate_completion(self) -> Tuple[bool, List[str]]:
        """
        Validate that proof-of-concept is complete and meets requirements.
        
        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []
        
        if not self.required:
            return True, []
        
        if not self.completed:
            errors.append("Proof-of-concept marked as incomplete")
        
        if not self.repository_url:
            errors.append("Repository URL is required for proof-of-concept")
        
        if not self.test_results_url:
            errors.append("Test results URL is required for proof-of-concept")
        
        if not self.completion_date:
            errors.append("Completion date is required")
        
        if len(self.acceptance_criteria) == 0:
            errors.append("At least one acceptance criterion is required")
        
        return len(errors) == 0, errors


class RFCProposal(SerializableModel):
    """
    RFC proposal for ASE protocol changes.
    """
    rfc_id: str = Field(..., alias="rfcId")
    title: str
    author: str
    author_email: str = Field(..., alias="authorEmail")
    category: RFCCategory
    status: RFCStatus
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    
    # Proposal content
    abstract: str
    motivation: str
    specification: str
    backward_compatibility: str = Field(..., alias="backwardCompatibility")
    security_considerations: str = Field(..., alias="securityConsiderations")
    
    # Proof-of-concept
    poc_requirement: ProofOfConceptRequirement = Field(..., alias="pocRequirement")
    
    # Review process
    reviewers: List[str] = []
    review_comments: List[Dict[str, Any]] = Field([], alias="reviewComments")
    approval_votes: Dict[str, bool] = Field({}, alias="approvalVotes")
    
    # Implementation tracking
    target_version: Optional[str] = Field(None, alias="targetVersion")
    implementation_pr: Optional[str] = Field(None, alias="implementationPr")
    implemented_at: Optional[datetime] = Field(None, alias="implementedAt")
    
    # Metadata
    related_rfcs: List[str] = Field([], alias="relatedRfcs")
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = Field(None, alias="supersededBy")
    
    def requires_poc(self) -> bool:
        """Check if this RFC requires a proof-of-concept."""
        # Categories that require POC
        poc_categories = {
            RFCCategory.PROTOCOL_EXTENSION.value,
            RFCCategory.SCHEMA_CHANGE.value,
            RFCCategory.SECURITY_ENHANCEMENT.value,
            RFCCategory.BACKWARD_COMPATIBILITY.value
        }
        return self.category in poc_categories
    
    def can_approve(self) -> Tuple[bool, List[str]]:
        """
        Check if RFC can be approved based on requirements.
        
        Returns:
            Tuple of (can_approve, list of blocking issues)
        """
        issues = []
        
        # Check status
        if self.status not in [RFCStatus.UNDER_REVIEW.value, RFCStatus.POC_COMPLETED.value]:
            issues.append(f"RFC must be under review or have completed POC, current status: {self.status}")
        
        # Check POC requirement
        if self.requires_poc():
            if not self.poc_requirement.required:
                issues.append("POC is required for this RFC category but not marked as required")
            
            poc_valid, poc_errors = self.poc_requirement.validate_completion()
            if not poc_valid:
                issues.extend([f"POC validation failed: {err}" for err in poc_errors])
        
        # Check minimum reviewers (at least 2)
        if len(self.reviewers) < 2:
            issues.append(f"At least 2 reviewers required, found {len(self.reviewers)}")
        
        # Check approval votes (at least 2 approvals, no rejections)
        approvals = sum(1 for vote in self.approval_votes.values() if vote)
        rejections = sum(1 for vote in self.approval_votes.values() if not vote)
        
        if approvals < 2:
            issues.append(f"At least 2 approval votes required, found {approvals}")
        
        if rejections > 0:
            issues.append(f"RFC has {rejections} rejection vote(s)")
        
        return len(issues) == 0, issues
    
    def add_review_comment(self, reviewer: str, comment: str, timestamp: Optional[datetime] = None):
        """Add a review comment to the RFC."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        self.review_comments.append({
            "reviewer": reviewer,
            "comment": comment,
            "timestamp": timestamp.isoformat()
        })
        self.updated_at = timestamp
    
    def add_approval_vote(self, reviewer: str, approved: bool):
        """Add an approval vote from a reviewer."""
        if reviewer not in self.reviewers:
            self.reviewers.append(reviewer)
        
        self.approval_votes[reviewer] = approved
        self.updated_at = datetime.now(timezone.utc)
    
    def transition_status(self, new_status: RFCStatus) -> Tuple[bool, Optional[str]]:
        """
        Transition RFC to a new status with validation.
        
        Returns:
            Tuple of (success, error_message)
        """
        # Define valid status transitions
        valid_transitions = {
            RFCStatus.DRAFT: [RFCStatus.SUBMITTED, RFCStatus.WITHDRAWN],
            RFCStatus.SUBMITTED: [RFCStatus.UNDER_REVIEW, RFCStatus.WITHDRAWN],
            RFCStatus.UNDER_REVIEW: [
                RFCStatus.POC_REQUIRED,
                RFCStatus.APPROVED,
                RFCStatus.REJECTED,
                RFCStatus.WITHDRAWN
            ],
            RFCStatus.POC_REQUIRED: [RFCStatus.POC_IN_PROGRESS, RFCStatus.WITHDRAWN],
            RFCStatus.POC_IN_PROGRESS: [RFCStatus.POC_COMPLETED, RFCStatus.WITHDRAWN],
            RFCStatus.POC_COMPLETED: [RFCStatus.UNDER_REVIEW, RFCStatus.APPROVED],
            RFCStatus.APPROVED: [RFCStatus.IMPLEMENTED],
            RFCStatus.REJECTED: [],
            RFCStatus.WITHDRAWN: [],
            RFCStatus.IMPLEMENTED: []
        }
        
        if new_status not in valid_transitions.get(self.status, []):
            return False, f"Invalid transition from {self.status.value} to {new_status.value}"
        
        # Additional validation for specific transitions
        if new_status == RFCStatus.APPROVED:
            can_approve, issues = self.can_approve()
            if not can_approve:
                return False, f"Cannot approve RFC: {'; '.join(issues)}"
        
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)
        
        # Set implementation date if transitioning to IMPLEMENTED
        if new_status == RFCStatus.IMPLEMENTED:
            self.implemented_at = datetime.now(timezone.utc)
        
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert RFC proposal to dictionary for serialization."""
        return {
            "rfcId": self.rfc_id,
            "title": self.title,
            "author": self.author,
            "authorEmail": self.author_email,
            "category": self.category.value,
            "status": self.status.value,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "abstract": self.abstract,
            "motivation": self.motivation,
            "specification": self.specification,
            "backwardCompatibility": self.backward_compatibility,
            "securityConsiderations": self.security_considerations,
            "pocRequirement": {
                "required": self.poc_requirement.required,
                "description": self.poc_requirement.description,
                "acceptanceCriteria": self.poc_requirement.acceptance_criteria,
                "implementationLanguage": self.poc_requirement.implementation_language,
                "repositoryUrl": self.poc_requirement.repository_url,
                "demoUrl": self.poc_requirement.demo_url,
                "testResultsUrl": self.poc_requirement.test_results_url,
                "completed": self.poc_requirement.completed,
                "completionDate": self.poc_requirement.completion_date.isoformat() if self.poc_requirement.completion_date else None,
                "reviewerNotes": self.poc_requirement.reviewer_notes
            },
            "reviewers": self.reviewers,
            "reviewComments": self.review_comments,
            "approvalVotes": self.approval_votes,
            "targetVersion": self.target_version,
            "implementationPr": self.implementation_pr,
            "implementedAt": self.implemented_at.isoformat() if self.implemented_at else None,
            "relatedRfcs": self.related_rfcs,
            "supersedes": self.supersedes,
            "supersededBy": self.superseded_by
        }


class RFCValidator:
    """
    Validator for RFC proposals and governance process compliance.
    
    Ensures that RFC proposals meet all requirements before approval,
    including proof-of-concept validation.
    """
    
    @staticmethod
    def validate_rfc_structure(rfc: RFCProposal) -> Tuple[bool, List[str]]:
        """
        Validate RFC proposal structure and required fields.
        
        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []
        
        # Validate RFC ID format (RFC-NNNN)
        if not rfc.rfc_id.startswith("RFC-") or not rfc.rfc_id[4:].isdigit():
            errors.append(f"Invalid RFC ID format: {rfc.rfc_id}, expected RFC-NNNN")
        
        # Validate required text fields
        if len(rfc.title) < 10:
            errors.append("Title must be at least 10 characters")
        
        if len(rfc.abstract) < 50:
            errors.append("Abstract must be at least 50 characters")
        
        if len(rfc.motivation) < 100:
            errors.append("Motivation must be at least 100 characters")
        
        if len(rfc.specification) < 200:
            errors.append("Specification must be at least 200 characters")
        
        if len(rfc.backward_compatibility) < 50:
            errors.append("Backward compatibility section must be at least 50 characters")
        
        if len(rfc.security_considerations) < 50:
            errors.append("Security considerations must be at least 50 characters")
        
        # Validate email format (basic check)
        if "@" not in rfc.author_email or "." not in rfc.author_email:
            errors.append(f"Invalid author email format: {rfc.author_email}")
        
        # Validate timestamps
        if rfc.updated_at < rfc.created_at:
            errors.append("Updated timestamp cannot be before created timestamp")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_poc_requirement(rfc: RFCProposal) -> Tuple[bool, List[str]]:
        """
        Validate proof-of-concept requirement for RFC.
        
        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []
        
        # Check if POC is required for this category
        if rfc.requires_poc():
            if not rfc.poc_requirement.required:
                errors.append(f"POC is required for category {rfc.category.value} but not marked as required")
            
            # Validate POC completion if RFC is being approved
            if rfc.status in [RFCStatus.POC_COMPLETED, RFCStatus.APPROVED]:
                poc_valid, poc_errors = rfc.poc_requirement.validate_completion()
                if not poc_valid:
                    errors.extend(poc_errors)
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_approval_readiness(rfc: RFCProposal) -> Tuple[bool, List[str]]:
        """
        Validate that RFC is ready for approval.
        
        Returns:
            Tuple of (is_ready, list of blocking issues)
        """
        all_errors = []
        
        # Validate structure
        structure_valid, structure_errors = RFCValidator.validate_rfc_structure(rfc)
        if not structure_valid:
            all_errors.extend([f"Structure: {err}" for err in structure_errors])
        
        # Validate POC
        poc_valid, poc_errors = RFCValidator.validate_poc_requirement(rfc)
        if not poc_valid:
            all_errors.extend([f"POC: {err}" for err in poc_errors])
        
        # Validate approval requirements
        can_approve, approval_errors = rfc.can_approve()
        if not can_approve:
            all_errors.extend([f"Approval: {err}" for err in approval_errors])
        
        return len(all_errors) == 0, all_errors
