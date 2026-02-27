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
    # Additional techniques for categorization manual labels
    SCRAPING_AND_RESEARCH = "scraping_and_research"
    TRIAGE = "triage"
    CONTENT_GENERATION = "content_generation"
    DOCUMENT_PROCESSING = "document_processing"
    DATA_EXTRACTION = "data_extraction"
    KNOWLEDGE_BASE = "knowledge_base"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"

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
    # Additional descriptions for manual categorization labels
    WorkflowTechnique.SCRAPING_AND_RESEARCH: "Extracting information from the web and conducting research",
    WorkflowTechnique.TRIAGE: "Prioritizing tasks or issues based on certain criteria",
    WorkflowTechnique.CONTENT_GENERATION: "Creating text, images, or other content using AI",
    WorkflowTechnique.DOCUMENT_PROCESSING: "Extracting and processing information from documents",
    WorkflowTechnique.DATA_EXTRACTION: "Pulling specific data points from larger datasets",
    WorkflowTechnique.KNOWLEDGE_BASE: "Storing and retrieving information in a structured way",
    WorkflowTechnique.HUMAN_IN_THE_LOOP: "Involving human judgment or input in the workflow"
}


@dataclass
class PromptCategorization:
    techniques: List[WorkflowTechnique]
    confidence: float
    reasoning: str = ""