from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from tortoise.exceptions import DoesNotExist

from ..services.auth import current_active_user, get_user_manager, UserManager
from ..models.user import User
from ..schemas.team import (
    TeamMemberRead,
    TeamMemberUpdate,
    TeamMemberCreate,
)
from ..config import rate_limit_dependency

router = APIRouter()


async def verify_admin_role(user: User = Depends(current_active_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can perform this action",
        )
    return user


@router.get("/members", response_model=List[TeamMemberRead], dependencies=[rate_limit_dependency])
async def get_team_members(user: User = Depends(verify_admin_role)):
    try:
        users = await User.filter(is_active=True)

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


@router.post("/members", status_code=status.HTTP_201_CREATED, dependencies=[rate_limit_dependency])
async def add_team_member(
    team_member: TeamMemberCreate,
    user: User = Depends(verify_admin_role),
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        new_user = await User.get_or_none(email=team_member.email)

        if new_user and new_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email {team_member.email} already exists",
            )

        if new_user and not new_user.is_active:
            new_user.is_active = True
            if team_member.password:
                new_user.hashed_password = user_manager.password_helper.hash(team_member.password)
            new_user.role = team_member.role
            await new_user.save()
            return TeamMemberRead(
                id=str(new_user.id),
                email=new_user.email,
                name=new_user.full_name or "",
                role=new_user.role,
                status="active" if new_user.is_active else "inactive",
                created_at=new_user.created_at.isoformat(),
            )

        hashed_password = user_manager.password_helper.hash(team_member.password)

        new_user = await User.create(
            email=team_member.email,
            role=team_member.role,
            is_active=True,
            is_superuser=False,
            is_verified=False,
            hashed_password=hashed_password,
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


@router.patch(
    "/members/{member_id}", response_model=TeamMemberRead, dependencies=[rate_limit_dependency]
)
async def update_member_role(
    member_id: str, update_data: TeamMemberUpdate, user: User = Depends(verify_admin_role)
):
    try:
        target_user = await User.get(id=member_id)

        target_user.role = update_data.role
        await target_user.save()

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


@router.delete(
    "/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[rate_limit_dependency],
)
async def remove_team_member(member_id: str, user: User = Depends(verify_admin_role)):
    try:
        target_user = await User.get(id=member_id)

        if str(target_user.id) == str(user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot remove yourself"
            )

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
