from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from typing import Optional, List

class Hint(BaseModel):
    hint: str
    point_cost: int

class CreateChallengeRequest(BaseModel):
    challenge_name: str
    points: int
    creator_name: str
    division: List[int]
    challenge_description: str
    flag: str
    is_flag_case_sensitive: bool
    challenge_category: str
    verified: bool
    solution_explanation: str
    hints: Optional[List[Hint]] = None

class ListChallengeResponse(BaseModel):
    challenge_name: str
    challenge_category: str
    points: int
    challenge_description: str
    challenge_id: str
    division: List[int]

class GetChallengeResponse(BaseModel):
	challenge_name: str
	points: int
	creator_name: str
	division: List[int]
	challenge_description: str
	flag: str
	is_flag_case_sensitive: bool
	challenge_category: str
	solution_explanation: str
	hints: Optional[List[Hint]] = None

class UserRole(str, Enum):
    admin = "admin"
    crimsonDefense = "crimson_defense"
    teacher = "teacher"

class LoginRequest(BaseModel):
    email: str
    password: str

class CreateCrimsonDefenseRequest(BaseModel):
    email: str

class CreateAdminRequest(BaseModel):
    email: str

class CreateTeacherRequest(BaseModel):
    first_name: str
    last_name: str
    school_name: str
    contact_number: str
    shirt_size: str
    email: str
    school_address: str
    school_website: str

class CreateCompetitionRequest(BaseModel):
    competition_name: str
    registration_deadline: datetime
    is_active: bool

class GetCompetitionResponse(BaseModel):
    competition_id: str
    competition_name: str
    registration_deadline: datetime
    is_active: bool

class CreateTeamRequest(BaseModel):
    teacher_id: str
    competition_id: str
    name: str
    division: int
    is_virtual: bool

class teacher_info(BaseModel):
    account_id: str
    first_name: str
    last_name: str
    school_name: str
    contact_number: str
    shirt_size: str
    school_address: str
    school_website: str

class student_info(BaseModel):
    student_account_id: str
    first_name: str
    last_name: str
    shirt_size: str
    liability_form: str
    upload_date: datetime
    is_verified: bool

class GetAllTeachersResponse(BaseModel):
    teachers: List[teacher_info]

class GetTeamByTeacherResponse(BaseModel):
    competition_id: str
    name: str
    division: int
    is_virtual: bool
    students: List[student_info]
