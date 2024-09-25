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


