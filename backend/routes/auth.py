"""
GreenPulse – Auth routes (POST /auth/register, /auth/login, GET/PUT /auth/me, POST /auth/change-password)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from config.database import get_db
from middleware.auth import hash_password, verify_password, create_access_token, get_current_user
from models.schemas import (
    UserRegister, UserLogin, TokenResponse, UserOut, MessageResponse,
    UserProfileUpdate, PasswordChange, UserRole
)
from utils.helpers import serialize_doc, now

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db=Depends(get_db)):
    """
    Public registration endpoint.
    STRICT PRIVILEGE ENFORCEMENT: All publicly registered users are unconditionally
    assigned the 'farmer' role. Public registration as 'admin' is strictly forbidden.
    """
    email_clean = data.email.lower().strip()
    if await db.users.find_one({"email": email_clean}):
        raise HTTPException(status_code=400, detail="Email already registered")

    user_doc = {
        "name":       data.name.strip(),
        "email":      email_clean,
        "password":   hash_password(data.password),
        "role":       UserRole.farmer.value,  # HARD-FORCED: never allow caller to elevate role
        "phone":      data.phone.strip() if data.phone else None,
        "village":    data.village.strip() if data.village else None,
        "crop":       data.crop.strip() if data.crop else None,
        "is_active":  True,
        "created_at": now(),
        "updated_at": None,
    }
    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id

    token = create_access_token({"sub": str(result.inserted_id), "role": UserRole.farmer.value})
    return TokenResponse(access_token=token, user=UserOut(**serialize_doc(user_doc)))


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db=Depends(get_db)):
    email_clean = data.email.lower().strip()
    user = await db.users.find_one({"email": email_clean})
    if not user or not verify_password(data.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account has been disabled. Please contact support.")

    token = create_access_token({"sub": str(user["_id"]), "role": user.get("role", "farmer")})
    return TokenResponse(access_token=token, user=UserOut(**serialize_doc(user)))


@router.get("/me", response_model=UserOut)
async def get_me(user=Depends(get_current_user)):
    return UserOut(**serialize_doc(user))


@router.put("/me", response_model=UserOut)
async def update_profile(
    data: UserProfileUpdate,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    update["updated_at"] = now()
    updated_user = await db.users.find_one_and_update(
        {"_id": user["_id"]},
        {"$set": update},
        return_document=True,
    )
    return UserOut(**serialize_doc(updated_user))


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: PasswordChange,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    if not verify_password(data.old_password, user.get("password", "")):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    if data.old_password == data.new_password:
        raise HTTPException(status_code=400, detail="New password cannot be the same as old password")

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password": hash_password(data.new_password), "updated_at": now()}}
    )
    return MessageResponse(message="Password updated successfully")


@router.post("/logout", response_model=MessageResponse)
async def logout():
    """Client-side token disposal endpoint."""
    return MessageResponse(message="Logged out successfully")
