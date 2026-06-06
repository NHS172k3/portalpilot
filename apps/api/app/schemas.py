from pydantic import BaseModel, Field


class AttributeIn(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=2000)
    sensitivity: str = "business"
    notes: str | None = None


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=240)


class ProfilePatch(BaseModel):
    name: str = Field(min_length=1, max_length=240)


class ResolveInfoIn(BaseModel):
    field_key: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=2000)


class ManualResearchIn(BaseModel):
    profile_id: str = Field(min_length=1, max_length=200)
    filing_need: str = Field(min_length=3, max_length=1000)


class AutoSuggestIn(BaseModel):
    profile_id: str = Field(min_length=1, max_length=200)
