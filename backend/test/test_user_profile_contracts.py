from sqlalchemy import String

from mvc.models.user_model import User
from mvc.schemas import UserResponse, UserUpdateRequest


def test_user_gender_profile_contract_accepts_text_values():
    assert isinstance(User.__table__.c.gender.type, String)

    update = UserUpdateRequest(gender="nonbinary")
    response = UserResponse(username="user", email="user@example.com", gender=update.gender)

    assert response.gender == "nonbinary"
