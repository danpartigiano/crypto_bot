from pydantic import BaseModel, EmailStr, Field

class User(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100, description="user first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="user last name")
    email: EmailStr = Field(..., description="user email")
    username: str = Field(..., min_length=5, max_length=100, description="user username")
    password: str = Field(..., min_length=12, max_length=100, description="user password")
