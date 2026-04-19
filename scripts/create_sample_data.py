#!/usr/bin/env python3
"""Generate sample CSV files for testing"""
import csv
import os
import random
from datetime import date, timedelta


CATEGORIES = ["inquiry", "complaint", "feedback", "request", "issue"]
PRIORITIES = ["low", "normal", "urgent"]
DESCRIPTIONS = [
    "Customer complaint about product delivery being significantly delayed",
    "Feature request for a new dashboard with real-time metrics",
    "Critical payment processing failure affecting all users",
    "Positive feedback on the latest UI update, users love it",
    "Inquiry about subscription billing and pricing changes",
    "Issue with password reset not sending confirmation emails",
    "Request for API access to integrate with third-party tools",
    "Complaint about poor customer support response times",
    "Bug report: application crashes on mobile devices",
    "Great experience with the onboarding process, very smooth",
]


def generate_sample_csv(filepath: str = "sample_data.csv", rows: int = 50) -> None:
    start_date = date(2026, 1, 1)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "date", "description", "category", "priority"])
        writer.writeheader()
        for i in range(1, rows + 1):
            row_date = start_date + timedelta(days=random.randint(0, 90))
            writer.writerow(
                {
                    "id": i,
                    "date": row_date.isoformat(),
                    "description": random.choice(DESCRIPTIONS),
                    "category": random.choice(CATEGORIES),
                    "priority": random.choice(PRIORITIES),
                }
            )
    print(f"Generated {rows} rows → {filepath}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate sample CSV data")
    parser.add_argument("--output", default="sample_data.csv", help="Output file path")
    parser.add_argument("--rows", type=int, default=50, help="Number of rows")
    args = parser.parse_args()
    generate_sample_csv(args.output, args.rows)
