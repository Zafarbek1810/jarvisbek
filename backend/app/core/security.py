import hashlib
import secrets
from datetime import datetime, timezone, timedelta
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.models import User, RefreshToken, AuditLog

hasher = PasswordHasher()
DUMMY_PASSWORD_HASH = hasher.hash(secrets.token_urlsafe(32))
bearer = HTTPBearer(auto_error=False)

def digest(token): return hashlib.sha256(token.encode()).hexdigest()

def verify(password, hashed):
    try: return hasher.verify(hashed, password)
    except (VerificationError, InvalidHashError): return False

def issue_tokens(db, user):
    cfg = get_settings()
    now = datetime.now(timezone.utc)
    access = jwt.encode({'sub': user.id, 'exp': now + timedelta(minutes=15), 'iat': now, 'jti': secrets.token_hex(16), 'type': 'access', 'iss': 'jarvis', 'aud': 'jarvis-clients'}, cfg.jwt_secret, algorithm='HS256')
    refresh = secrets.token_urlsafe(48)
    db.add(RefreshToken(owner_id=user.id, token_hash=digest(refresh), expires_at=now + timedelta(days=14)))
    db.commit()
    return {'access_token': access, 'refresh_token': refresh, 'token_type': 'bearer', 'user': {'id': user.id, 'name': user.name, 'email': user.email}}

def current_user(auth: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    try:
        if not auth: raise ValueError()
        data = jwt.decode(auth.credentials, get_settings().jwt_secret, algorithms=['HS256'], issuer='jarvis', audience='jarvis-clients', options={'require': ['sub', 'exp', 'type', 'iss', 'aud']})
        if data['type'] != 'access': raise ValueError()
        user = db.get(User, data['sub'])
        if user: return user
    except (jwt.InvalidTokenError, ValueError): pass
    raise HTTPException(401, 'Hisobingizga kiring.')

def audit(db, user_id, action, resource_id='', detail=None):
    db.add(AuditLog(owner_id=user_id, action=action, resource_id=resource_id, detail=detail or {}))


def owned(db, model, item_id, user_id):
    row = db.scalar(select(model).where(model.id == item_id, model.owner_id == user_id))
    if row is None: raise HTTPException(404, 'Ma’lumot topilmadi.')
    return row
