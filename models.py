# For more details, see
# http://docs.sqlalchemy.org/en/latest/orm/tutorial.html#declare-a-mapping
from anthill.framework.db import db
from anthill.framework.utils import timezone
from anthill.framework.utils.translation import translate_lazy as _
from anthill.framework.utils.asynchronous import as_future
from anthill.platform.api.internal import InternalAPIMixin
from anthill.platform.auth import RemoteUser
from sqlalchemy_utils.types import ChoiceType
from functools import partial


class Group(InternalAPIMixin, db.Model):
    __tablename__ = 'groups'

    TYPES = (
        ('p', _('Personal')),
        ('m', _('Multiple')),
        ('c', _('Channel')),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    type = db.Column(ChoiceType(TYPES))
    created = db.Column(db.DateTime, default=timezone.now)
    updated = db.Column(db.DateTime, onupdate=timezone.now)
    active = db.Column(db.Boolean, nullable=False, default=True)

    @as_future
    def get_messages(self, user_id=None, **kwargs) -> dict:
        default_kwargs = dict(active=True)
        if user_id is not None:
            default_kwargs.update(sender_id=user_id)
        default_kwargs.update(kwargs)
        data = {
            'model_name': 'Message',
            'filter_data': default_kwargs
        }
        return self.internal_request('message', 'get_models', **data)

    @as_future
    def get_memberships(self, user_id=None, **kwargs):
        default_kwargs = dict(active=True)
        if user_id is not None:
            default_kwargs.update(user_id=user_id)
        default_kwargs.update(kwargs)
        return self.memberships.filter_by(**default_kwargs)


class GroupMembership(InternalAPIMixin, db.Model):
    __tablename__ = 'groups_memberships'

    group_id = db.Column(db.Integer, db.ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True)
    user_id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=timezone.now)
    active = db.Column(db.Boolean, nullable=False, default=True)
    group = db.relationship('Group', backref=db.backref('memberships', lazy='dynamic'))
    notify_by_message = db.Column(db.Boolean, nullable=False, default=True)
    notify_by_email = db.Column(db.Boolean, nullable=False, default=False)
    # TODO: permissions

    @property
    def request_user(self):
        return partial(self.internal_request, 'login', 'get_user')

    async def get_receiver(self) -> RemoteUser:
        data = await self.request_user(user_id=self.user_id)
        return RemoteUser(**data)


@as_future
def get_friends(user_id):
    membership_query = GroupMembership.query.join(Group)
    friendships1 = membership_query.filter(Group.type == 'p').filter_by(active=True, user_id=user_id)
    friendships2 = membership_query.filter(
        GroupMembership.user_id != user_id, Group.id.in_(f.group_id for f in friendships1))
    return (f.user_id for f in friendships2)


@as_future
def make_friends(user_id1, user_id2):
    # TODO: check if already friends
    group = Group.create(type='p', name=None)  # TODO: name
    GroupMembership.create(user_id=user_id1, group_id=group.id)
    GroupMembership.create(user_id=user_id2, group_id=group.id)


@as_future
def remove_friends(user_id1, user_id2):
    Group.query.filter_by(type='p', name=None).first().delete()  # TODO: name

