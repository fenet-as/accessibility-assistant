"""HTTP request/response bodies that are specific to the REST API (not domain entities)."""

from typing import List, Optional

from pydantic import BaseModel, Field


class EscalationRequest(BaseModel):
    session: str = Field(default="anon-session")
    reason: str = Field(default="Need tutor assistance", max_length=500)
    language: str = Field(default="en")


class JobCreateRequest(BaseModel):
    title: str = Field(..., description="Job title, e.g. 'Junior Data Annotator'")
    company_name: str = Field(..., description="Hiring organization name, e.g. 'EthioTech Hub'")
    description: str = Field(..., description="Job role and responsibilities")
    location: str = Field(default="Addis Ababa", description="Locality, e.g. 'Addis Ababa' or 'Remote'")
    country: str = Field(default="ET", description="Country code (ISO 3166-1 alpha-2)")
    employment_type: str = Field(default="FULL_TIME", description="'FULL_TIME', 'PART_TIME', 'CONTRACT', 'REMOTE'")
    alternate_name: Optional[str] = Field(default=None, description="Short display title, e.g. 'Data Annotator'")
    qualifications: Optional[str] = Field(default=None, description="Key skills and requirements")
    accommodations_offered: List[str] = Field(
        default_factory=list,
        description="Accessibility accommodations offered, e.g. ['Screen reader friendly', 'Flexible hours']",
    )


class AccommodationRequest(BaseModel):
    job_id: str = Field(..., description="Target job vacancy ID")
    accommodations: List[str] = Field(
        ..., description="e.g. ['extra_time', 'screen_reader_materials', 'accessible_venue']"
    )
    contact_channel: str = Field(..., description="e.g. 'telegram' or 'phone'")
    contact_value: str = Field(..., description="Handle or number")


class SubscriptionRequest(BaseModel):
    channel: str = Field(..., description="'telegram' or 'sms'")
    contact: str = Field(..., description="Phone number or Telegram chat ID")
    category: str = Field(default="all", description="Job category preference")


class SMSInboundRequest(BaseModel):
    sender: str = Field(default="+251911000000", description="Originating phone number")
    body: str = Field(..., max_length=1600, description="SMS message text")


class IngestRequest(BaseModel):
    course_id: str = Field(..., description="Unique course identifier, e.g. 'course:python-101'")
    course_title: str = Field(..., description="Human-readable course title")
    lesson_url: str = Field(default="/pages/lesson.html", description="Lesson URL on the LMS")
    content_type: str = Field(default="markdown", description="'markdown' or 'html'")
    content: str = Field(..., description="Raw lesson text in Markdown or HTML")


class IngestResponse(BaseModel):
    status: str
    course_id: str
    chunks_created: int
    sections: List[str]
    sample_url: str
