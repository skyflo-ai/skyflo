from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..config import rate_limit_dependency
from ..models.integration import IntegrationRead, IntegrationCreate, IntegrationUpdate
from ..services.integrations import IntegrationService
from ..services.auth import current_active_user
from ..models.user import User

router = APIRouter()


async def verify_admin_role(user: User = Depends(current_active_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can perform this action",
        )
    return user


@router.post("/", response_model=IntegrationRead, dependencies=[rate_limit_dependency])
async def create_integration(payload: IntegrationCreate, user: User = Depends(verify_admin_role)):
    try:
        service = IntegrationService()
        created = await service.create_integration(
            created_by_user_id=str(user.id),
            provider=payload.provider,
            metadata=payload.metadata,
            credentials=payload.credentials,
            name=payload.name,
        )
        return IntegrationRead.model_validate(created)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create integration: {str(e)}",
        )


@router.get("/", response_model=List[IntegrationRead], dependencies=[rate_limit_dependency])
async def list_integrations(
    provider: Optional[str] = Query(default=None), user: User = Depends(current_active_user)
):
    try:
        service = IntegrationService()
        items = await service.list_integrations(provider=provider)
        return [IntegrationRead.model_validate(i) for i in items]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list integrations: {str(e)}",
        )


@router.patch(
    "/{integration_id}", response_model=IntegrationRead, dependencies=[rate_limit_dependency]
)
async def update_integration(
    integration_id: str, payload: IntegrationUpdate, user: User = Depends(verify_admin_role)
):
    try:
        service = IntegrationService()
        updated = await service.update_integration(
            integration_id=integration_id,
            metadata=payload.metadata,
            credentials=payload.credentials,
            name=payload.name,
            status=payload.status,
        )
        return IntegrationRead.model_validate(updated)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update integration: {str(e)}",
        )


@router.delete(
    "/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[rate_limit_dependency],
)
async def delete_integration(
    integration_id: str,
    user: User = Depends(verify_admin_role),
):
    try:
        service = IntegrationService()
        await service.delete_integration(integration_id=integration_id)
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete integration: {str(e)}",
        )
