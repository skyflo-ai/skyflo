"""Team management endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from tortoise.exceptions import DoesNotExist

from api.domain.models.user import User, UserRead
from api.web.endpoints.auth import current_active_user
from api.domain.schemas.team import (
    TeamMemberRead,
    TeamMemberUpdate,
    TeamMemberCreate,
)

router = APIRouter()


async def verify_admin_role(user: User = Depends(current_active_user)):
    """Verify that the current user has admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can perform this action",
        )
    return user


@router.get("/members", response_model=List[TeamMemberRead])
async def get_team_members(user: User = Depends(verify_admin_role)):
    """
    Get all team members.
    Only accessible to users with admin role.
    """
    try:
        # Get all users in the system
        users = await User.filter(is_active=True)

        # Convert to TeamMemberRead format
        return [
            TeamMemberRead(
                id=str(user.id),
                email=user.email,
                name=user.full_name or "",
                role=user.role,
                status="active" if user.is_active else "inactive",
                created_at=user.created_at.isoformat(),
            )
            for user in users
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch team members: {str(e)}",
        )


@router.post("/members", status_code=status.HTTP_201_CREATED)
async def add_team_member(team_member: TeamMemberCreate, user: User = Depends(verify_admin_role)):
    """
    Add a team member.
    Only accessible to users with admin role.
    """
    try:
        # Get the user to add
        new_user = await User.get_or_none(email=team_member.email)

        if new_user and new_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email {team_member.email} already exists",
            )

        if new_user and not new_user.is_active:
            new_user.is_active = True
            await new_user.save()
            return TeamMemberRead(
                id=str(new_user.id),
                email=new_user.email,
                name=new_user.full_name or "",
                role=new_user.role,
                status="active" if new_user.is_active else "inactive",
                created_at=new_user.created_at.isoformat(),
            )

        # Create a new user with the specified role (or default "member") and password
        new_user = await User.create(
            email=team_member.email,
            role=team_member.role,
            is_active=True,
            is_superuser=False,
            is_verified=False,
            hashed_password=team_member.password,  # Use the provided password
        )

        return TeamMemberRead(
            id=str(new_user.id),
            email=new_user.email,
            name=new_user.full_name or "",
            role=new_user.role,
            status="active" if new_user.is_active else "inactive",
            created_at=new_user.created_at.isoformat(),
        )
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add team member: {str(e)}",
        )


@router.patch("/members/{member_id}", response_model=TeamMemberRead)
async def update_member_role(
    member_id: str, update_data: TeamMemberUpdate, user: User = Depends(verify_admin_role)
):
    """
    Update a team member's role.
    Only accessible to users with admin role.
    """
    try:
        # Get the user to update
        target_user = await User.get(id=member_id)

        # Update the role
        target_user.role = update_data.role
        await target_user.save()

        # Return the updated user
        return TeamMemberRead(
            id=str(target_user.id),
            email=target_user.email,
            name=target_user.full_name or "",
            role=target_user.role,
            status="active" if target_user.is_active else "inactive",
            created_at=target_user.created_at.isoformat(),
        )
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team member with ID {member_id} not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update team member: {str(e)}",
        )


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(member_id: str, user: User = Depends(verify_admin_role)):
    """
    Remove a team member.
    Only accessible to users with admin role.
    """
    try:
        # Get the user to remove
        target_user = await User.get(id=member_id)

        # Don't allow removing yourself
        if str(target_user.id) == str(user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot remove yourself"
            )

        # Disable the user instead of deleting
        target_user.is_active = False
        await target_user.save()

        return None
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team member with ID {member_id} not found",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove team member: {str(e)}",
        )
