from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

# from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.schemas.users import ProfileResponse
from app.services.users import my_profile
from app.db.models.users import User
from app.auth.auth_model.Ulogin import User_tb
from app.auth.schema.auth_U import UserSignUpRequest, UserSignUpResponse, UserLoginResponse
from app.auth.utils.utils import hashing_password, verify_password
from app.auth.auth_db import get_db
from jose import ExpiredSignatureError, jwt, JWTError #
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone

from app.core.secret_keys import settings

SECRET_KEY = settings.ssetting.secret_key
ALGORITHM = settings.ssetting.algorithm
SACCESS_TOKEN_EXPIRE_MINUTES = settings.ssetting.access_token_expire_minutes
value = SACCESS_TOKEN_EXPIRE_MINUTES

# import os
# from dotenv import load_dotenv
# load_dotenv()
# SECRET_KEY = os.getenv("SSECRET_KEY")
# ALGORITHM = os.getenv("SALGORITHM")
# # SACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("SACCESS_TOKEN_EXPIRE_MINUTES")
# value = os.getenv("SACCESS_TOKEN_EXPIRE_MINUTES", "30")
if value is None:
    SACCESS_TOKEN_EXPIRE_MINUTES = 30
else:
    SACCESS_TOKEN_EXPIRE_MINUTES = int(value)

"""
Helper function that take user data and create JWT token
copy that data so original doesnt modify
set expire time = now + 30min
adds expiry field to token payload
"""
def create_access_token(data: dict):
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=SACCESS_TOKEN_EXPIRE_MINUTES)
    payload.update({'exp': expire, 'type': 'access'}) #JWT automatically check
    # payload["exp"] = expire #both are same
    jwt_token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    return jwt_token


router = APIRouter()

"""
Create an endpoint which take userdata(UserSignUpRequest model)& db,
(query)check user exist or not?,

"""
@router.post("/signup")
async def register_user(user: UserSignUpRequest, db: AsyncSession = Depends(get_db)):
    user_name = user.username.strip()
    email_of_user = user.email.strip().lower()
    query = select(User).where((User.username == user_name) | (User.email_id == email_of_user))
    result = await db.execute(query)
    user_exist = result.scalars().first()
    if user_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or Email already exist!!"
        )
    
    # hash the password
    h_password = hashing_password(user.password)
    
    # create new_user instance
    new_user = User(
        username = user_name,
        email_id = email_of_user,
        role = user.role
    )
    # save user in db
    db.add(new_user)
    await db.flush()

    new_cred = User_tb(
        user_id = new_user.id,
        hashed_password = h_password
    )
    db.add(new_cred)
    await db.commit()
    await db.refresh(new_user)
    await db.refresh(new_cred)
    # return the value (excluding password)
    return UserSignUpResponse(
        id = new_user.id,
        username = new_user.username,
        email = new_user.email_id,
        role = new_user.role
    )


@router.post("/login", response_model=UserLoginResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    identifier = form_data.username.strip()
    query = select(User).where((User.username == identifier) | (User.email_id == identifier)).options(selectinload(User.credential))
    result = await db.execute(query)
    user = result.scalars().first()
    if not user or not user.credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # user.id->123, user.credential->User_tb, user.credential.hashed_password->"hashedps"
    if not verify_password(form_data.password, user.credential.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token_data = {"sub": str(user.id), "role": user.role}
    token = create_access_token(token_data)
    # return {"access_token": token, "token_type": "bearer"}
    return UserLoginResponse(access_token=token, token_type="bearer")
    # if user is None:
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Username!!")
    # if not verify_password(form_data.password, user.hashed_password):
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Password!!")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, 
        detail="Couldn't validate credentials", 
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise credential_exception
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if not user_id or not role:
            raise credential_exception
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Expired!!")
    except JWTError:
        raise credential_exception
    try:
        user_uuid = UUID(user_id)
    except Exception:
        raise credential_exception
    query_user_exist = select(User.id).where(User.id == user_uuid)
    result_user_exist = await db.execute(query_user_exist) 
    user_exit_in_db = result_user_exist.scalar_one_or_none()
    if not user_exit_in_db:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists (account deleted)")

    return {"sub": str(user_uuid), "role": role}


def require_roles(allowed_roles: list[str]):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role")
        if user_role == "admin":
            return current_user
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Not enough permission for {user_role}"
            )
        return current_user
    return role_checker

@router.get("/profile", response_model=ProfileResponse)
async def profile(db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_roles(["user", "admin"]))):
    my_profile_detail = await my_profile(db, current_user["sub"])
    return {
        "message": f"Profile of {current_user['sub']} ({current_user['role']})",
        "detail": my_profile_detail
    }

@router.get("/user/dashboard")
async def user_dashboard(current_user: dict = Depends(require_roles(["user"]))):
    return {"message": "Welcome User"}

@router.get("/admin/dashboard")
async def admin_dashboard(current_admin: dict = Depends(require_roles(["admin"]))):
    return {"message": "Welcome Admin"}

