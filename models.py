# models.py
from pydantic import BaseModel, Field
from typing import Optional, List


class ExtractedCaseSchema(BaseModel):
    """Fields the LLM is asked to extract from the OCR'd text."""
    gstins: List[str] = Field(default_factory=list, description="List of GSTINs found, e.g. ['27AAAFP6015C1ZQ']")
    trade_names: List[str] = Field(default_factory=list, description="List of trade/legal names, same order as gstins")
    case_summary: Optional[str] = Field(None, description="Concise summary of the nature of the case")
    category_suggestion: Optional[str] = Field(
        None,
        description="One of 'Fake ITC', 'Issue-based', 'Reference from Audit', 'Others'"
    )
    date_of_approval: Optional[str] = Field(None, description="Date of Pr. Commissioner's approval, YYYY-MM-DD")


class CaseRecord(BaseModel):
    """Full record as stored in the central data sheet. One Serial_No (case
    file) can carry more than one GSTIN / trade name, stored as '; '-joined
    strings in the same order."""
    Serial_No: Optional[int] = None
    GSTINs: Optional[str] = None
    Trade_Names: Optional[str] = None
    Case_Summary: Optional[str] = None
    Category: Optional[str] = None
    Investigation_Group: Optional[str] = None
    Status: Optional[str] = None
    Date_of_Approval: Optional[str] = None
    Uploaded_By: Optional[str] = None
    Uploaded_On: Optional[str] = None
    Photo_Links: Optional[str] = None
