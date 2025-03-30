from app.schemas.user_schema import UserSchema
from app.models.user_model import User
from app.core.security import get_password_hash
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

class UserService:
    @staticmethod
    async def create_user(user: UserSchema, db: AsyncSession):
        new_user = User(
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            username=user.username,
            hashed_password=get_password_hash(user.password)
        )

        try:
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
        
        except IntegrityError:
            await db.rollback()
            return None
        
        return new_user

        

        