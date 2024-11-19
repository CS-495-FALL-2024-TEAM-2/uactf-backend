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
    challenge_file_attachment: Optional[str]

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
    liability_release_form: str

class EmailRequest(BaseModel):
    email_account: str
    subject: str
    message: str

class EmailWithAttachmentRequest(BaseModel):
    email_account: str
    subject: str
    message: str
    attachment_content: Optional[str] = None
    attachment_filename: Optional[str] = None

class CreateStudentRequest(BaseModel):
    first_name: str
    last_name: str
    shirt_size: str
    email: Optional[str] = None

class CreateTeamRequest(BaseModel):
    teacher_id: Optional[str] = None
    name: str
    division: List[int]
    is_virtual: bool
    team_members: List[CreateStudentRequest]


class TeacherInfo(BaseModel):
    id: str
    account_id: str
    first_name: str
    last_name: str
    school_name: str
    school_address: str
    school_website: str
    contact_number: str
    shirt_size: str


class StudentInfoResponse(BaseModel):
    id: str
    student_account_id: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    shirt_size: str
    signed_liability_release_form: Optional[str] = None
    is_verified: bool

class GetAllTeachersResponse(BaseModel):
    teachers: List[TeacherInfo]

class GetTeamResponse(BaseModel):
    id: str
    teacher_id: str
    competition_id: str
    name: str
    division: List[int]
    is_virtual: bool
    students: List[StudentInfoResponse]

class ForgotPasswordRequest(BaseModel):
    email: str

class CreateTeamsReportRequest(BaseModel):
    is_virtual: bool
    email: Optional[str] = None

class CreateStudentAccountsReportRequest(BaseModel):
    email: Optional[str] = None
    is_verified: Optional[bool] = True

