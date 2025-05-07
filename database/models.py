from tortoise.models import Model
from tortoise import fields


class User(Model):
    id = fields.BigIntField(primary_key=True)
    first_name = fields.CharField(max_length=255)

    social_credit = fields.FloatField(default=0)


class SuspiciousMessage(Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="suspicious_messages")

    message = fields.TextField()
    timestamp = fields.DatetimeField(auto_now_add=True)


