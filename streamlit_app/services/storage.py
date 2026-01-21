"""Cloud storage service for investment reports using Supabase.

This module handles uploading reports to Supabase Storage and
storing metadata in the Supabase PostgreSQL database for querying
historical reports.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None


BUCKET_NAME = "investment-reports"


@dataclass
class ReportMetadata:
    """Metadata for a stored report."""
    id: str
    ticker: str
    company_name: str
    created_at: datetime
    storage_path: str
    markdown_url: Optional[str]
    equity_pdf_url: Optional[str]
    memo_pdf_url: Optional[str]
    status: str


class StorageService:
    """Handles report storage in Supabase."""

    def __init__(self):
        """Initialize Supabase client."""
        if not SUPABASE_AVAILABLE:
            raise ImportError("supabase package not installed")

        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY environment variables must be set"
            )

        self.client: Client = create_client(url, key)

    def upload_report(
        self,
        ticker: str,
        company_name: str,
        markdown_path: Optional[Path] = None,
        equity_pdf_path: Optional[Path] = None,
        memo_pdf_path: Optional[Path] = None,
        chart_paths: Optional[List[Path]] = None,
    ) -> ReportMetadata:
        """
        Upload all report files to Supabase storage.

        Args:
            ticker: Stock ticker symbol
            company_name: Company name
            markdown_path: Path to markdown report
            equity_pdf_path: Path to equity research PDF
            memo_pdf_path: Path to investment memo PDF
            chart_paths: List of paths to chart images

        Returns:
            ReportMetadata with URLs to uploaded files
        """
        # Create unique storage path with timestamp
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        storage_path = f"{ticker}/{timestamp}"

        urls = {}

        # Upload markdown report
        if markdown_path and markdown_path.exists():
            urls["markdown"] = self._upload_file(
                markdown_path, f"{storage_path}/report.md"
            )

        # Upload equity research PDF
        if equity_pdf_path and equity_pdf_path.exists():
            urls["equity_pdf"] = self._upload_file(
                equity_pdf_path, f"{storage_path}/equity_research.pdf"
            )

        # Upload investment memo PDF
        if memo_pdf_path and memo_pdf_path.exists():
            urls["memo_pdf"] = self._upload_file(
                memo_pdf_path, f"{storage_path}/investment_memo.pdf"
            )

        # Upload chart images
        if chart_paths:
            for chart_path in chart_paths:
                if chart_path.exists():
                    self._upload_file(
                        chart_path, f"{storage_path}/charts/{chart_path.name}"
                    )

        # Store metadata in database
        record = self.client.table("reports").insert({
            "ticker": ticker,
            "company_name": company_name,
            "storage_path": storage_path,
            "markdown_url": urls.get("markdown"),
            "equity_pdf_url": urls.get("equity_pdf"),
            "memo_pdf_url": urls.get("memo_pdf"),
            "status": "completed",
        }).execute()

        return self._record_to_metadata(record.data[0])

    def _upload_file(self, local_path: Path, remote_path: str) -> str:
        """
        Upload a single file to storage and return its public URL.

        Args:
            local_path: Path to local file
            remote_path: Destination path in storage bucket

        Returns:
            Public URL of uploaded file
        """
        content_type = self._get_content_type(local_path)

        with open(local_path, "rb") as f:
            file_data = f.read()

        self.client.storage.from_(BUCKET_NAME).upload(
            remote_path,
            file_data,
            file_options={"content-type": content_type}
        )

        return self.client.storage.from_(BUCKET_NAME).get_public_url(remote_path)

    def _get_content_type(self, path: Path) -> str:
        """Determine content type from file extension."""
        ext = path.suffix.lower()
        content_types = {
            ".md": "text/markdown",
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        return content_types.get(ext, "application/octet-stream")

    def get_reports_for_ticker(self, ticker: str) -> List[ReportMetadata]:
        """
        Get all historical reports for a specific ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of ReportMetadata ordered by date (newest first)
        """
        result = self.client.table("reports").select("*").eq(
            "ticker", ticker.upper()
        ).order("created_at", desc=True).execute()

        return [self._record_to_metadata(r) for r in result.data]

    def get_recent_reports(self, limit: int = 20) -> List[ReportMetadata]:
        """
        Get most recent reports across all tickers.

        Args:
            limit: Maximum number of reports to return

        Returns:
            List of ReportMetadata ordered by date (newest first)
        """
        result = self.client.table("reports").select("*").order(
            "created_at", desc=True
        ).limit(limit).execute()

        return [self._record_to_metadata(r) for r in result.data]

    def get_report_by_id(self, report_id: str) -> Optional[ReportMetadata]:
        """
        Get a specific report by its ID.

        Args:
            report_id: UUID of the report

        Returns:
            ReportMetadata or None if not found
        """
        result = self.client.table("reports").select("*").eq(
            "id", report_id
        ).execute()

        if result.data:
            return self._record_to_metadata(result.data[0])
        return None

    def get_chart_urls(self, storage_path: str) -> List[str]:
        """
        Get URLs for all charts in a report's storage path.

        Args:
            storage_path: Storage path of the report (e.g., "AAPL/2024-01-15T10-30-00")

        Returns:
            List of public URLs for chart images
        """
        try:
            charts_path = f"{storage_path}/charts"
            files = self.client.storage.from_(BUCKET_NAME).list(charts_path)
            return [
                self.client.storage.from_(BUCKET_NAME).get_public_url(
                    f"{charts_path}/{f['name']}"
                )
                for f in files
                if f["name"].endswith((".png", ".jpg", ".jpeg"))
            ]
        except Exception:
            return []

    def _record_to_metadata(self, record: dict) -> ReportMetadata:
        """Convert database record to ReportMetadata."""
        created_at = record.get("created_at", "")
        if isinstance(created_at, str):
            # Handle ISO format with timezone
            created_at = created_at.replace("Z", "+00:00")
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                created_at = datetime.utcnow()

        return ReportMetadata(
            id=record["id"],
            ticker=record["ticker"],
            company_name=record.get("company_name", ""),
            created_at=created_at,
            storage_path=record.get("storage_path", ""),
            markdown_url=record.get("markdown_url"),
            equity_pdf_url=record.get("equity_pdf_url"),
            memo_pdf_url=record.get("memo_pdf_url"),
            status=record.get("status", "completed"),
        )


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> Optional[StorageService]:
    """
    Get or create storage service instance.

    Returns None if Supabase is not configured.
    """
    global _storage_service

    if _storage_service is not None:
        return _storage_service

    # Check if Supabase is configured
    if not SUPABASE_AVAILABLE:
        return None

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        return None

    try:
        _storage_service = StorageService()
        return _storage_service
    except Exception:
        return None


def is_storage_configured() -> bool:
    """Check if cloud storage is properly configured."""
    return get_storage_service() is not None
