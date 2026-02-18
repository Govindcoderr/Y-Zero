# types/categorization.py
from typing import List
from enum import Enum
from dataclasses import dataclass

class WorkflowTechnique(str, Enum):
    SCHEDULING = "scheduling"
    API_INTEGRATION = "api_integration"
    DATA_TRANSFORMATION = "data_transformation"
    NOTIFICATION = "notification"
    CHATBOT = "chatbot"
    DATA_ANALYSIS = "data_analysis"
    FORM_INPUT = "form_input"
    MONITORING = "monitoring"
    SCRAPING = "scraping"
    ENRICHMENT = "enrichment"

TECHNIQUE_DESCRIPTIONS = {
    WorkflowTechnique.SCHEDULING: "Running actions at specific times or intervals",
    WorkflowTechnique.API_INTEGRATION: "Calling external APIs or webhooks",
    WorkflowTechnique.DATA_TRANSFORMATION: "Cleaning, formatting, or restructuring data",
    WorkflowTechnique.NOTIFICATION: "Sending alerts via email, chat, SMS",
    WorkflowTechnique.CHATBOT: "Conversational interfaces",
    WorkflowTechnique.DATA_ANALYSIS: "Analyzing data for patterns or insights",
    WorkflowTechnique.FORM_INPUT: "Gathering data from users via forms",
    WorkflowTechnique.MONITORING: "Checking service status and alerting",
    WorkflowTechnique.SCRAPING: "Extracting data from websites",
    WorkflowTechnique.ENRICHMENT: "Adding extra details to existing data",
}

@dataclass
class PromptCategorization:
    techniques: List[WorkflowTechnique]
    confidence: float
    reasoning: str = ""