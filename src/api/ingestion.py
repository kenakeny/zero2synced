# Parse uploaded CSV/Excel files and push them to S3 so the agent can
# ingest them via a Fivetran S3 connector.
import io
import os
from dataclasses import dataclass

import pandas as pd


@dataclass
class ParsedFile:
    columns: list[str]
    row_count: int
    sample_rows: list[dict]
    csv_bytes: bytes  # normalized to CSV regardless of input format


def parse_file(filename: str, raw: bytes) -> ParsedFile:
    name = filename.lower()
    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(raw))
    elif name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(raw))
    else:
        raise ValueError(f"Unsupported file type: {filename}. Use CSV or Excel.")

    if df.empty:
        raise ValueError("The file has no rows.")

    return ParsedFile(
        columns=[str(c) for c in df.columns],
        row_count=len(df),
        sample_rows=df.head(5).astype(str).to_dict(orient="records"),
        csv_bytes=df.to_csv(index=False).encode("utf-8"),
    )


def upload_to_s3(csv_bytes: bytes, key: str) -> str | None:
    """Returns the s3:// URI, or None when S3 isn't configured (context-only fallback)."""
    bucket = os.getenv("S3_BUCKET")
    if not bucket:
        return None
    import boto3
    s3 = boto3.client("s3")
    s3.put_object(Bucket=bucket, Key=key, Body=csv_bytes)
    return f"s3://{bucket}/{key}"


def build_agent_notification(filename: str, parsed: ParsedFile, s3_uri: str | None) -> str:
    cols = ", ".join(parsed.columns)
    msg = (
        f"[SYSTEM NOTE] The user just uploaded a file: {filename} "
        f"({parsed.row_count} rows; columns: {cols}). "
        f"Sample rows: {parsed.sample_rows[:3]}. "
    )
    if s3_uri:
        msg += (
            f"The file is available at {s3_uri} for ingestion via an S3 connector. "
            "Briefly summarize what's in the file in plain English and offer to bring "
            "this data into their destination. Follow your normal confirm-before-create rule."
        )
    else:
        msg += (
            "Cloud storage isn't configured, so this file can only be used as context. "
            "Briefly summarize what's in the file and how it relates to the user's goal."
        )
    return msg
