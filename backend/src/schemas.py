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
