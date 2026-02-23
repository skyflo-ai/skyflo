"""Refresh token model definition."""

import uuid

from tortoise import fields, models


class RefreshToken(models.Model):
    """Refresh token model for rotating tokens."""

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    token_hash = fields.CharField(max_length=64, unique=True, index=True)
    user = fields.ForeignKeyField(
        "models.User", related_name="refresh_tokens", on_delete=fields.CASCADE
    )
    expires_at = fields.DatetimeField()
    revoked_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "refresh_tokens"

    def __str__(self) -> str:
        return f"<RefreshToken {self.id} user={self.user_id}>"
