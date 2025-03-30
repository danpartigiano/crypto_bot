from schemas import UserAuth
from utils import get_password_hash
from models import User

class UserService:
    @staticmethod
    async def create_user(user: UserAuth):
        user_in = User(
            username=user.username,
            email=user.email,
            hashed_password=get_password_hash(user.password)
        )
        await user_in.save()