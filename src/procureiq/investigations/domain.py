"""Validated workflow and typed application failures."""
from enum import Enum


class Status(str,Enum):
    OPEN='OPEN'
    INVESTIGATING='INVESTIGATING'
    REVIEWED='REVIEWED'
    CLOSED='CLOSED'


class Disposition(str,Enum):
    FURTHER_ACTION_RECOMMENDED='FURTHER_ACTION_RECOMMENDED'
    NO_ACTIONABLE_FINDING='NO_ACTIONABLE_FINDING'
    INSUFFICIENT_EVIDENCE='INSUFFICIENT_EVIDENCE'


class InvestigationError(Exception):
    def __init__(self,code,message,status=409):
        self.code,self.message,self.status=code,message,status
        super().__init__(message)


def meaningful(value,minimum=10,maximum=4000):
    return isinstance(value,str) and minimum<=len(value.strip())<=maximum and sum(c.isalnum() for c in value)>=5


def transition(old,new,reason=None,disposition=None):
    allowed={'OPEN':'INVESTIGATING','INVESTIGATING':'REVIEWED','REVIEWED':'CLOSED','CLOSED':'INVESTIGATING'}
    if allowed.get(old)!=new:raise InvestigationError('invalid_transition','Follow OPEN → INVESTIGATING → REVIEWED → CLOSED; closed cases can explicitly reopen to INVESTIGATING.')
    if new=='CLOSED':
        if disposition not in {d.value for d in Disposition} or not meaningful(reason):
            raise InvestigationError('invalid_closure','Closing requires a disposition and a meaningful explanation of at least 10 characters.',422)
    elif disposition is not None:raise InvestigationError('invalid_input','Disposition is only accepted when closing.',422)
    if old=='CLOSED' and not meaningful(reason):raise InvestigationError('reopen_reason_required','Reopening requires a meaningful written reason of at least 10 characters.',422)
    if reason is not None and not meaningful(reason):raise InvestigationError('invalid_input','Reasons must be meaningful text of 10–4000 characters.',422)
