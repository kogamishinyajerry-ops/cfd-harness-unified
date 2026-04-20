"""Public surface for the report engine."""

from .contract_dashboard import ContractDashboardGenerator
from .data_collector import ReportDataCollector
from .generator import ReportGenerator
from .visual_acceptance import VisualAcceptanceReportGenerator

__all__ = [
    "ContractDashboardGenerator",
    "ReportGenerator",
    "ReportDataCollector",
    "VisualAcceptanceReportGenerator",
]
