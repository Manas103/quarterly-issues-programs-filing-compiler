"""Generates the actual quarterly issues-and-programs filing document
(Word), populated programmatically from a `FilingList` the compiler
computed. Nothing in this document is hand-typed; every row in the
segment table comes from `qipc.compiler.build_filing_list`.
"""

from __future__ import annotations

from datetime import date

from docx import Document
from docx.shared import Pt

from qipc.categories import CATEGORIES
from qipc.compiler import FilingList


def _add_segment_table(document: Document, segments) -> None:
    table = document.add_table(rows=1, cols=4)
    table.style = "Light Grid Accent 1"
    header = table.rows[0].cells
    for i, label in enumerate(("Air date", "Air time", "Duration (min)", "Narrative")):
        header[i].text = label
    for seg in segments:
        cells = table.add_row().cells
        cells[0].text = seg.air_date
        cells[1].text = seg.air_time
        cells[2].text = str(seg.duration_min)
        cells[3].text = seg.narrative


def build_filing_document(filing: FilingList, station_name: str, call_sign: str,
                           generated_on: date, output_path: str) -> None:
    doc = Document()
    doc.styles["Normal"].font.size = Pt(10.5)

    doc.add_heading("Quarterly Issues and Programs List", level=0)
    doc.add_paragraph(
        f"{station_name} ({call_sign}) -- {filing.quarter.label} "
        f"({filing.quarter.start_date.isoformat()} to {filing.quarter.end_date.isoformat()})"
    )
    doc.add_paragraph(f"Generated {generated_on.isoformat()}.")
    doc.add_paragraph(
        "This list and the station, call sign, segment content and narratives in "
        "it are synthetic, generated for this project. No real station or broadcast "
        "is represented. This document is machine-generated from measured compiler "
        "output; no segment row below was hand-typed. This is not legal advice; it "
        "is a reasonable software implementation of the public 47 CFR 73.3526 rule, "
        "not a substitute for counsel."
    )

    doc.add_heading("1. Reporting Period and Filing Deadline", level=1)
    doc.add_paragraph(
        f"1.1 This list reports on community issues and the programs that addressed "
        f"them for {filing.quarter.label}, as required by 47 CFR 73.3526."
    )
    doc.add_paragraph(
        f"1.2 Statutory filing deadline (10th day of the succeeding calendar "
        f"quarter): {filing.filing_deadline}."
    )
    doc.add_paragraph(
        f"1.3 Total airtime devoted to community issues this quarter: "
        f"{filing.quarter_total} minutes across {len(filing.all_segments)} segments."
    )

    doc.add_heading("2. Community Issues Addressed", level=1)
    doc.add_paragraph(
        "2.1 The station's weekly public-affairs program addressed the following "
        f"{len(CATEGORIES)} community issues this quarter, each with the specific "
        "segments that covered it."
    )

    for i, category in enumerate(CATEGORIES, start=1):
        segs = filing.segments_by_category.get(category, [])
        total = filing.category_totals.get(category, 0)
        doc.add_heading(f"2.{i} {category}", level=2)
        doc.add_paragraph(
            f"{len(segs)} segment(s), {total} minute(s) total airtime this quarter."
        )
        if segs:
            _add_segment_table(doc, segs)
        else:
            doc.add_paragraph("No segments addressed this issue this quarter.")

    doc.add_heading("3. Least-Airtime Summary", level=1)
    doc.add_paragraph(
        "3.1 See the accompanying coverage deck for the full ranking of all "
        "8 issues by total airtime, ascending (least-covered first)."
    )

    doc.add_heading("4. Certification", level=1)
    doc.add_paragraph("4.1 Prepared by: __________________________  Date: ______________")
    doc.add_paragraph("4.2 Filed by: _____________________________  Date: ______________")

    doc.save(output_path)
