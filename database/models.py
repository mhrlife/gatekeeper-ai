from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.BigIntField(primary_key=True)
    first_name = fields.CharField(max_length=255)

    social_credit = fields.FloatField(default=0)


class SuspiciousMessage(Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="suspicious_messages")

    message = fields.TextField()
    timestamp = fields.DatetimeField(auto_now_add=True)


class GroupInfo(Model):
    id = fields.BigIntField(primary_key=True)

    name = fields.CharField(max_length=255, default="")
    description = fields.TextField(default="")
    rules_context = fields.TextField(default="")

    owner = fields.ForeignKeyField("models.User", related_name="owned_groups")


class UserGroupMessage(Model):
    id = fields.BigIntField(primary_key=True, generated=True) # Auto-incrementing PK
    user = fields.ForeignKeyField("models.User", related_name="group_messages")
    group = fields.ForeignKeyField("models.GroupInfo", related_name="user_messages")
    message_id = fields.BigIntField() # Telegram's message ID
    text = fields.TextField()
    message_created_at = fields.DatetimeField() # Timestamp from Telegram message
    replied_to_message_id = fields.BigIntField(null=True)
    replied_to_message_text = fields.TextField(null=True)
    db_created_at = fields.DatetimeField(auto_now_add=True) # For ordering and pruning

    class Meta:
        ordering = ["-db_created_at"] # Default ordering for queries
