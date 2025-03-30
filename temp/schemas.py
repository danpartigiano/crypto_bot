from pydantic import BaseModel, EmailStr, Field

#Request Models
class UserAuth(BaseModel):
    username: str = Field(..., min_length=5, max_length=50, description="user username")
    password: str = Field(..., min_length=12, max_length=50, description="user password")
    email: EmailStr = Field(..., description="user email")

#Response Models
class UserOut(BaseModel):
    username: str
    email: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
