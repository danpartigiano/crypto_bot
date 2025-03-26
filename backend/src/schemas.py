from pydantic import BaseModel

#Request Models
class UserAuth(BaseModel):
    username: str
    password: str
    email: str

#Response Models
class UserOut(BaseModel):
    username: str
    email: str

class Token(BaseModel):
    access_token: str
    refresh_token: str



class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str
