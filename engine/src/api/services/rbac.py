"""Role-based access control (RBAC) service using PyCasbin."""

import uuid
from typing import Optional, List
import logging

import casbin
from casbin import persist
from casbin import Enforcer
from casbin.model import Model
from tortoise.transactions import atomic


logger = logging.getLogger(__name__)

# Define the role model
CASBIN_MODEL_TEXT = """
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && (r.obj == p.obj || p.obj == '*') && (r.act == p.act || p.act == '*')
"""

# Global enforcer instance
_enforcer: Optional[Enforcer] = None


class TortoiseAdapter(persist.Adapter):
    """Tortoise ORM adapter for PyCasbin policy storage."""

    async def load_policy(self, model: Model) -> None:
        """Load policy from database."""
        # In a real implementation, we would load policies from a database
        # For this example, we'll use a hardcoded set of policies

        # Company-level roles
        model.add_policy("p", "p", ["company_admin", "company_*", "*"])
        model.add_policy("p", "p", ["company_manager", "company_*", "read"])
        model.add_policy("p", "p", ["company_manager", "company_*", "write"])

        # Team-level roles
        model.add_policy("p", "p", ["team_admin", "team_*", "*"])
        model.add_policy("p", "p", ["team_manager", "team_*", "read"])
        model.add_policy("p", "p", ["team_manager", "team_*", "write"])
        model.add_policy("p", "p", ["team_member", "team_*", "read"])

        # Conversation-level roles
        model.add_policy("p", "p", ["conversation_owner", "conversation_*", "*"])
        model.add_policy("p", "p", ["conversation_viewer", "conversation_*", "read"])

        # Role inheritance
        model.add_policy("g", "g", ["company_admin", "team_admin"])
        model.add_policy("g", "g", ["team_admin", "team_manager"])
        model.add_policy("g", "g", ["team_manager", "team_member"])

    async def save_policy(self, model: Model) -> bool:
        """Save policy to database."""
        # In a real implementation, we would save updated policies to a database
        return True


async def init_enforcer() -> None:
    """Initialize the Casbin enforcer."""
    global _enforcer

    if _enforcer is None:
        # Create model from text
        model = casbin.Model()
        model.load_model_from_text(CASBIN_MODEL_TEXT)

        # Create adapter
        adapter = TortoiseAdapter()

        # Create enforcer without auto-loading policies
        _enforcer = casbin.Enforcer(model, None)  # Initialize with no adapter first
        _enforcer.enable_auto_save(False)  # Disable auto-save to prevent unexpected sync calls
        _enforcer.enable_auto_build_role_links(False)  # Disable auto role link building

        # Set the adapter
        _enforcer.adapter = adapter

        # Manually load policies using the async method
        await adapter.load_policy(_enforcer.get_model())

        # Build role links after loading policies
        _enforcer.build_role_links()

        logger.info("PyCasbin enforcer initialized with async policy loading")


async def get_enforcer() -> Enforcer:
    """Get the Casbin enforcer instance."""
    global _enforcer

    if _enforcer is None:
        await init_enforcer()

    return _enforcer


async def check_permission(user_id: uuid.UUID, resource: str, action: str) -> bool:
    """Check if a user has permission to perform an action on a resource."""
    enforcer = await get_enforcer()
    return enforcer.enforce(str(user_id), resource, action)


@atomic()
async def assign_role(
    user_id: uuid.UUID, role: str, resource_id: Optional[uuid.UUID] = None
) -> None:
    """Assign a role to a user for a specific resource."""
    enforcer = await get_enforcer()

    if resource_id:
        # Role for a specific resource
        enforcer.add_grouping_policy(str(user_id), f"{role}_{resource_id}")
    else:
        # Global role
        enforcer.add_grouping_policy(str(user_id), role)

    # Rebuild role links after modifying policies
    enforcer.build_role_links()

    logger.debug(f"Assigned role {role} to user {user_id}")


@atomic()
async def remove_role(
    user_id: uuid.UUID, role: str, resource_id: Optional[uuid.UUID] = None
) -> None:
    """Remove a role from a user for a specific resource."""
    enforcer = await get_enforcer()

    if resource_id:
        # Role for a specific resource
        enforcer.remove_grouping_policy(str(user_id), f"{role}_{resource_id}")
    else:
        # Global role
        enforcer.remove_grouping_policy(str(user_id), role)

    # Rebuild role links after modifying policies
    enforcer.build_role_links()

    logger.debug(f"Removed role {role} from user {user_id}")


async def get_user_roles(user_id: uuid.UUID) -> List[str]:
    """Get all roles assigned to a user."""
    enforcer = await get_enforcer()
    roles: List[List[str]] = enforcer.get_roles_for_user(str(user_id))
    return [role[0] for role in roles] if roles else []
