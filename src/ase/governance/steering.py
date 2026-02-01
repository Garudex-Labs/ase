"""
ASE Steering Committee Governance.

Defines the committee structure and oversight mechanisms for the ASE protocol.
"""

from typing import List, Optional
from datetime import datetime, timezone
from pydantic import Field
from ase.core.serialization import SerializableModel


class CommitteeMember(SerializableModel):
    """Member of the ASE Steering Committee."""
    member_id: str = Field(..., alias="memberId")
    name: str
    organization: str
    appointed_at: datetime = Field(..., alias="appointedAt")
    role: str = Field("member", description="Member role (e.g., chair, secretary)")


class SteeringCommittee(SerializableModel):
    """
    ASE Steering Committee management.
    """
    members: List[CommitteeMember] = []
    charter_url: Optional[str] = Field(None, alias="charterUrl")
    last_meeting: Optional[datetime] = Field(None, alias="lastMeeting")

    def add_member(self, member: CommitteeMember):
        """Add a new member to the committee."""
        self.members.append(member)

    def remove_member(self, member_id: str):
        """Remove a member by ID."""
        self.members = [m for m in self.members if m.member_id != member_id]

    def get_member(self, member_id: str) -> Optional[CommitteeMember]:
        """Look up a member."""
        for m in self.members:
            if m.member_id == member_id:
                return m
        return None
