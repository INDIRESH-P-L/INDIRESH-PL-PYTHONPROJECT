from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os

def create_pdf_presentation():
    output_path = os.path.join(os.path.dirname(__file__), "Expense_Tracker_Presentation.pdf")
    doc = SimpleDocTemplate(output_path, pagesize=landscape(letter),
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    Story = []
    styles = getSampleStyleSheet()

    # Custom Styles
    styles.add(ParagraphStyle(name='CustomTitle', 
                              parent=styles['Title'], 
                              fontSize=40, 
                              leading=50, 
                              alignment=TA_CENTER, 
                              textColor=HexColor('#3b82f6'),
                              spaceAfter=20))
                              
    styles.add(ParagraphStyle(name='CustomSubtitle', 
                              parent=styles['Normal'], 
                              fontSize=18, 
                              leading=24, 
                              alignment=TA_CENTER, 
                              textColor=HexColor('#6b7280')))
                              
    styles.add(ParagraphStyle(name='SlideTitle', 
                              parent=styles['Heading1'], 
                              fontSize=28, 
                              leading=34, 
                              alignment=TA_LEFT, 
                              textColor=HexColor('#8b5cf6'),
                              spaceAfter=20,
                              spaceBefore=20))
                              
    styles.add(ParagraphStyle(name='BulletPoint', 
                              parent=styles['Normal'], 
                              fontSize=18, 
                              leading=26, 
                              alignment=TA_LEFT,
                              spaceAfter=15,
                              bulletFontName='Helvetica',
                              bulletFontSize=18,
                              bulletIndent=15,
                              leftIndent=35))

    def add_title_slide(title_text, subtitle_text=""):
        Story.append(Spacer(1, 2*inch))
        Story.append(Paragraph(title_text, styles["CustomTitle"]))
        Story.append(Paragraph(subtitle_text, styles["CustomSubtitle"]))
        Story.append(PageBreak())

    def add_content_slide(title_text, bullet_points):
        Story.append(Paragraph(title_text, styles["SlideTitle"]))
        for point in bullet_points:
            Story.append(Paragraph(f"<bullet>&bull;</bullet>{point.strip()}", styles["BulletPoint"]))
        Story.append(PageBreak())

    # --- Content ---

    # Slide 1: Title
    add_title_slide("Expense Tracker Application", "A modern, responsive, and robust personal finance management tool")

    # Slide 2: Introduction
    intro_points = [
        "An interactive web application built with Python (Flask) and SQLite.",
        "Helps users track their daily income and expenses easily and efficiently.",
        "Provides a comprehensive dashboard summarizing financial health.",
        "Visualizes spending patterns through category-wise breakdown."
    ]
    add_content_slide("1. Introduction", intro_points)

    # Slide 3: Problem Statement
    problem_points = [
        "Keeping track of daily spending is difficult using traditional notebooks or complex spreadsheets.",
        "Lack of immediate visibility into personal balance can lead to overspending.",
        "Users struggle to identify which categories (e.g., Food, Travel) consume most of their income.",
        "There is a need for a lightweight, accessible tool that prevents expenses from exceeding total income."
    ]
    add_content_slide("2. Problem Statement", problem_points)

    # Slide 4: Innovation Ideas
    innovation_points = [
        "Real-time Income Guard: Automatically blocks users from adding an expense if it exceeds total income.",
        "Premium UI/UX: Custom-designed dashboard with dynamic color mapping and micro-animations.",
        "Zero-Config Setup: Self-contained SQLite database with auto-initialization.",
        "Dynamic Visualizations: Auto-adjusting category bars mapping out spending by importance."
    ]
    add_content_slide("3. Innovation Ideas in the Project", innovation_points)

    # Slide 5: Software Used
    software_points = [
        "Backend Core: Python 3",
        "Web Framework & Server: Flask + Waitress WSGI",
        "Database: SQLite (Built-in standard library)",
        "Frontend Structure: HTML5",
        "Styling: Vanilla CSS (Custom modern design system)",
        "Interactivity: Vanilla JavaScript"
    ]
    add_content_slide("4. Software Used", software_points)

    # Slide 6: Number of Modules
    module_points = [
        "Core Modules: expencetrack.py (Routing) and HTML Templates.",
        "Python Standard Libraries: os, sqlite3, datetime.",
        "Third-Party Packages: flask, waitress.",
        "Total Core Conceptual Modules: 3 (Backend Logic, Database Manager, Frontend UI)"
    ]
    add_content_slide("5. Number of Modules Used", module_points)

    # Build the PDF
    doc.build(Story)
    print(f"Presentation saved successfully to {output_path}")

if __name__ == "__main__":
    create_pdf_presentation()
