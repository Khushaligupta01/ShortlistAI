"""
Generates deterministic synthetic resume fixtures for Phase 4 testing.
All candidate names, emails, and phone numbers are completely synthetic.
"""
import io
import os
from pathlib import Path

import docx
import fitz  # PyMuPDF

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "resumes"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


def create_pdf(filename: str, pages_text: list[str]) -> Path:
    out_path = FIXTURES_DIR / filename
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page(width=612, height=792)  # Standard letter
        # Write text with margin
        rect = fitz.Rect(50, 50, 562, 742)
        page.insert_textbox(rect, text, fontsize=11, fontname="helv", color=(0, 0, 0))
    doc.save(str(out_path))
    doc.close()
    return out_path


def create_docx(filename: str, paragraphs: list[str], tables: list[list[list[str]]] = None) -> Path:
    out_path = FIXTURES_DIR / filename
    doc = docx.Document()
    for p in paragraphs:
        doc.add_paragraph(p)

    if tables:
        for t_data in tables:
            rows = len(t_data)
            cols = len(t_data[0]) if rows > 0 else 0
            table = doc.add_table(rows=rows, cols=cols)
            for r_idx, row in enumerate(t_data):
                for c_idx, cell_value in enumerate(row):
                    table.cell(r_idx, c_idx).text = cell_value

    doc.save(str(out_path))
    return out_path


def main():
    print("Generating synthetic resume fixtures in:", FIXTURES_DIR)

    # 1. Strong Java Developer Profile (PDF)
    text_01 = """Aarav Sharma
San Jose, CA | aarav.sharma@example.com | +1-555-0101
Notice Period: 30 days

PROFESSIONAL SUMMARY
Senior Java Engineer with 8 years of experience designing high-scale microservices, distributed messaging pipelines, and cloud native architectures.

TECHNICAL SKILLS
Languages: Java, SQL, Python
Frameworks & Libraries: Spring Boot, Spring Cloud, Hibernate
Databases & Messaging: PostgreSQL, Redis, Apache Kafka
Cloud & DevOps: AWS, Docker, Kubernetes, Git, REST API

WORK EXPERIENCE
Senior Java Engineer | Apex Tech Solutions, San Jose, CA
Jan 2020 - Present
- Architected and deployed 12 Spring Boot microservices handling over 50k transactions/sec.
- Implemented real-time event streaming using Apache Kafka and PostgreSQL.
- Containerized enterprise services with Docker and orchestrated workloads on Kubernetes.

Java Developer | FinSoft Systems, Sunnyvale, CA
June 2016 - Dec 2019
- Developed REST APIs using Spring Boot, Hibernate, and Oracle DB.
- Reduced database query latency by 40% through Redis caching strategies.

EDUCATION
Bachelor of Science in Computer Science
Stanford University | Graduated 2016
"""
    create_pdf("01_strong_java_senior.pdf", [text_01])

    # 2. Partial Java Developer Profile (DOCX)
    paras_02 = [
        "Bhavna Patel",
        "Austin, TX | bhavna.patel@example.com | +1-555-0102",
        "Notice Period: 60 days",
        "Summary: Software Engineer with 4 years of experience building Java web applications.",
        "Skills: Java, Spring Boot, MySQL, REST API, Git, HTML, CSS",
        "Experience:",
        "Java Developer at Innovate Corp (Jan 2020 - Present)",
        "- Built RESTful web services using Java and Spring Boot.",
        "- Maintained MySQL database schemas and wrote stored procedures.",
        "Junior Developer at WebCore LLC (Aug 2019 - Dec 2019)",
        "- Assisted in Java bug fixing and unit testing with JUnit.",
        "Education: Bachelor of Science in Information Technology, UT Austin, 2019",
    ]
    create_docx("02_partial_java_developer.docx", paras_02)

    # 3. Weak Match Profile - Marketing (PDF)
    text_03 = """Charles Davis
Chicago, IL | charles.davis@example.com | +1-555-0103
Notice Period: Immediate (0 days)

PROFESSIONAL SUMMARY
Digital Marketing Manager with 6 years experience specializing in SEO, SEM, content strategy, and social media campaigns.

CORE SKILLS
Search Engine Optimization (SEO), Google Analytics, HubSpot, Content Marketing, Social Media Strategy, Copywriting.

EXPERIENCE
Digital Marketing Lead | BrandVelocity, Chicago, IL
Mar 2021 - Present
- Managed paid acquisition budgets across Google Ads and LinkedIn.
- Grew organic search traffic by 150% in 18 months through strategic SEO.

Marketing Specialist | MediaPulse Inc.
Jun 2018 - Feb 2021
- Created email nurture workflows and coordinated blog content production.

EDUCATION
BA in Communications, Northwestern University, 2018
"""
    create_pdf("03_weak_match_marketing.pdf", [text_03])

    # 4. Resume Missing Location (DOCX)
    paras_04 = [
        "Deepa Nair",
        "deepa.nair@example.com | +1-555-0104",
        "Notice Period: 15 days",
        "Summary: Backend Engineer with 5 years experience in Python and cloud services.",
        "Technical Skills: Python, FastAPI, Django, Docker, PostgreSQL, Redis",
        "Experience:",
        "Python Engineer | CloudScale Systems (2021 - Present)",
        "- Designed high-performance APIs using FastAPI and async Python.",
        "Education: B.Tech in Computer Science, 2019",
    ]
    create_docx("04_missing_location.docx", paras_04)

    # 5. Resume Missing Notice Period (PDF)
    text_05 = """Ethan Brown
Seattle, WA | ethan.brown@example.com | +1-555-0105

SUMMARY
Java Backend Developer with 5 years of enterprise application development experience.

SKILLS
Java, Spring Boot, Hibernate, Oracle, JUnit, Git, Maven

EXPERIENCE
Java Developer | Emerald City Software, Seattle, WA
Feb 2019 - Present
- Developed core banking modules using Spring Boot and Oracle database.
- Implemented secure REST endpoints authenticated via OAuth2.

EDUCATION
BS in Computer Science, University of Washington, 2019
"""
    create_pdf("05_missing_notice_period.pdf", [text_05])

    # 6. Resume Missing Experience Duration (DOCX)
    paras_06 = [
        "Fiona Gallagher",
        "Boston, MA | fiona.g@example.com | +1-555-0106",
        "Notice Period: 30 days",
        "Skills: Java, Spring Boot, SQL, Docker",
        "Experience:",
        "Software Engineer at Boston Tech Labs",
        "- Developed backend microservices in Java.",
        "Junior Programmer at Harbor Innovations",
        "- Maintained legacy Java applications and wrote automated unit tests.",
        "Education: BS in Computer Engineering, Northeastern University",
    ]
    create_docx("06_missing_experience_duration.docx", paras_06)

    # 7. Exact Duplicate File (Copy of 01)
    doc_01 = (FIXTURES_DIR / "01_strong_java_senior.pdf").read_bytes()
    (FIXTURES_DIR / "07_duplicate_exact.pdf").write_bytes(doc_01)

    # 8. Malformed PDF
    (FIXTURES_DIR / "08_malformed.pdf").write_bytes(b"%PDF-1.4\n%corrupted garbage bytes " + os.urandom(256))

    # 9. Empty PDF
    (FIXTURES_DIR / "09_empty.pdf").write_bytes(b"")

    # 10. DOCX With Tables
    paras_10 = [
        "George Vance",
        "Denver, CO | george.v@example.com | +1-555-0110",
        "Notice Period: 30 days",
        "Skills: Java, Spring Boot, AWS, Kubernetes, PostgreSQL",
    ]
    tables_10 = [
        [
            ["Company", "Role", "Dates", "Description"],
            ["Peak Technologies", "Senior Java Developer", "2021 - Present", "Built Kubernetes microservices"],
            ["MileHigh Data", "Java Software Engineer", "2018 - 2021", "Maintained Spring Boot payment gateway"],
        ],
        [
            ["Degree", "Institution", "Year"],
            ["B.S. Software Engineering", "Colorado State University", "2018"],
        ],
    ]
    create_docx("10_docx_with_tables.docx", paras_10, tables=tables_10)

    # 11. Multi-page PDF
    page1 = """Hannah Abbott - Page 1
New York, NY | hannah.abbott@example.com | +1-555-0111
Notice Period: 30 days
Total Experience: 10 years

SUMMARY
Principal Java Architect with extensive experience leading distributed cloud platforms.

TECHNICAL PROFICIENCIES
Java, Spring Cloud, Kafka, Docker, Kubernetes, AWS, PostgreSQL, MongoDB, Reactive Programming

CORE EXPERIENCE
Lead Architect | Gotham FinTech Solutions (2020 - Present)
- Led team of 15 engineers designing multi-tenant wealth management platform.
- Transitioned monolithic architecture into 25 microservices running on AWS EKS.
"""
    page2 = """Hannah Abbott - Page 2
Gotham FinTech Solutions (Continued)
- Designed high-throughput Kafka ingestion engine handling 100M events/day.
- Implemented zero-downtime blue/green deployment strategies.

Senior Java Engineer | Manhattan Data Systems (2016 - 2020)
- Built distributed low-latency algorithmic trading feeds in Java.
- Optimized JVM garbage collection reducing p99 latency by 65%.
"""
    page3 = """Hannah Abbott - Page 3
EDUCATION & CERTIFICATIONS
Master of Science in Distributed Systems | Columbia University (2016)
Bachelor of Science in Computer Science | NYU (2014)

CERTIFICATIONS
- AWS Certified Solutions Architect Professional (2022)
- Certified Kubernetes Administrator (CKA) (2021)
"""
    create_pdf("11_multipage_java_lead.pdf", [page1, page2, page3])

    # 12. Resume With Unusual Formatting (PDF)
    text_12 = (
        "Ian Wright\t\t\tian.wright@example.com\n"
        "Philadelphia, PA\t\t+1-555-0112\n"
        "Notice\u00a0Period:\u00a030\u00a0days\n\n"
        "\u25cf Skills: Java\u00a0\u00a0•\u00a0\u00a0Spring Boot\u00a0\u00a0•\u00a0\u00a0C++\u00a0\u00a0•\u00a0\u00a0.NET\u00a0\u00a0•\u00a0\u00a0SQL\n\n"
        "\u25b8 Professional Experience:\n"
        "Lead Developer  ---  Liberty Softworks (2019 - Present)\n"
        "  - Built resilient C++ and Java services for data processing.\n"
        "  - Optimized database queries for SQL Server and PostgreSQL.\n\n"
        "Education:\n"
        "B.S. in Computer Science | Penn State (2019)\n"
    )
    create_pdf("12_unusual_formatting.pdf", [text_12])

    # 13. Scanned PDF Without Extractable Text (Image only)
    doc_13 = fitz.open()
    page_13 = doc_13.new_page(width=612, height=792)
    # Draw shapes simulating a scanned document page without any text layer
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 400, 500), 1)
    pix.clear_with(240)  # Light gray
    page_13.insert_image(fitz.Rect(50, 50, 500, 700), pixmap=pix)
    doc_13.save(str(FIXTURES_DIR / "13_scanned_image_ocr_required.pdf"))
    doc_13.close()

    # 14. Resume Containing Conflicting Dates (DOCX)
    paras_14 = [
        "Julia Zhang",
        "j.zhang@example.com | +1-555-0114 | San Diego, CA",
        "Notice Period: 30 days",
        "Skills: Java, Python, SQL",
        "Experience:",
        "Senior Java Developer | Pacific Tech (2023 - 2021)",  # End date before start date!
        "- Developed backend services.",
        "Java Developer | BaySoft (2022 - Present)",  # Overlapping concurrent dates
        "- Maintained APIs.",
        "Education: BS Computer Science, UC San Diego, 2020",
    ]
    create_docx("14_conflicting_dates.docx", paras_14)

    print("Successfully generated all 14 synthetic fixtures.")


if __name__ == "__main__":
    main()
