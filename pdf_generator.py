import os
import datetime
import logging
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

logger = logging.getLogger("pdf_generator")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUOTATIONS_DIR = os.path.join(BASE_DIR, "quotations")

def generate_wholesale_quotation_pdf(user_id: int, customer_name: str, customer_phone: str, cart_items: list) -> str:
    """Generates a professional branded wholesale quotation PDF for AT SELECTION."""
    if not os.path.exists(QUOTATIONS_DIR):
        os.makedirs(QUOTATIONS_DIR, exist_ok=True)
        
    timestamp = int(datetime.datetime.now().timestamp())
    quotation_no = f"Q-{timestamp % 100000:05d}"
    date_str = datetime.datetime.now().strftime("%d/%m/%Y %I:%M %p")
    pdf_filename = f"AT_SELECTION_Quotation_{quotation_no}.pdf"
    pdf_path = os.path.join(QUOTATIONS_DIR, pdf_filename)
    
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1A237E')
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-BoldOblique',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#C62828')
    )
    
    body_bold = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#212121')
    )
    
    body_regular = ParagraphStyle(
        'BodyReg',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#424242')
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white,
        alignment=1 # Centered
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#212121')
    )
    
    story = []
    
    # 1. HEADER SECTION
    logo_path = os.path.join(BASE_DIR, "logo.jpg")
    header_data = []
    
    shop_info_text = Paragraph(
        "<b><font size=16 color='#1A237E'>AT SELECTION</font></b><br/>"
        "<b><font size=10 color='#C62828'>WHOLESALE READYMADE GARMENTS</font></b><br/>"
        "<font size=8 color='#424242'>1st Floor, Shop 7,8,9, City Plaza Complex, Dewan Dewdi, Hyderabad, T.S.<br/>"
        "<b>Owner:</b> Syed Ahmer (+91 9701515477 / 8019924400)</font>",
        styles['Normal']
    )
    
    if os.path.exists(logo_path):
        try:
            img = Image(logo_path, width=1.1*inch, height=1.1*inch)
            header_table = Table([[img, shop_info_text]], colWidths=[1.3*inch, 5.7*inch])
        except Exception:
            header_table = Table([[shop_info_text]], colWidths=[7.0*inch])
    else:
        header_table = Table([[shop_info_text]], colWidths=[7.0*inch])
        
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    
    # Gold / Red divider bar
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#FF6F00'), spaceAfter=12))
    
    # 2. QUOTATION METADATA BOX
    clean_phone = customer_phone if customer_phone else str(user_id)
    meta_left = Paragraph(
        f"<b>OFFICIAL WHOLESALE ESTIMATE & QUOTATION</b><br/>"
        f"<b>Quotation No:</b> <font color='#1A237E'><b>#{quotation_no}</b></font><br/>"
        f"<b>Date:</b> {date_str}",
        body_regular
    )
    meta_right = Paragraph(
        f"<b>CUSTOMER DETAILS:</b><br/>"
        f"<b>Name / Business:</b> {customer_name}<br/>"
        f"<b>WhatsApp Contact:</b> +{clean_phone}",
        body_regular
    )
    
    meta_table = Table([[meta_left, meta_right]], colWidths=[3.5*inch, 3.5*inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F5F5F5')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E0E0E0')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))
    
    # 3. ITEMIZED PRODUCTS TABLE
    table_data = [
        [
            Paragraph("S.No", table_header_style),
            Paragraph("Item ID", table_header_style),
            Paragraph("Garment Name & Category", table_header_style),
            Paragraph("Sizes", table_header_style),
            Paragraph("Qty (Sets)", table_header_style),
            Paragraph("Rate/Set (Est.)", table_header_style),
            Paragraph("Amount (₹)", table_header_style),
        ]
    ]
    
    total_sets = 0
    total_amount = 0.0
    
    for idx, item in enumerate(cart_items, 1):
        pid = item.get("product_id") or item.get("id") or idx
        pname = item.get("name", "Wholesale Garment")
        pcat = item.get("category", "General")
        psizes = item.get("sizes", "Standard")
        qty = item.get("quantity", 1)
        price = float(item.get("price", 0.0))
        
        # If price is 0 (quotation request mode), estimate average set rate if needed
        if price <= 0:
            price = 650.0 # Default estimated wholesale benchmark rate
            
        line_total = price * qty
        total_sets += qty
        total_amount += line_total
        
        item_title = f"<b>{pname}</b><br/><font size=7 color='#616161'>Category: {pcat}</font>"
        
        table_data.append([
            Paragraph(str(idx), table_cell_style),
            Paragraph(f"#{pid}", table_cell_style),
            Paragraph(item_title, table_cell_style),
            Paragraph(str(psizes), table_cell_style),
            Paragraph(f"{qty} set(s)", table_cell_style),
            Paragraph(f"₹{price:,.2f}", table_cell_style),
            Paragraph(f"<b>₹{line_total:,.2f}</b>", table_cell_style),
        ])
        
    prod_table = Table(
        table_data,
        colWidths=[0.4*inch, 0.7*inch, 2.5*inch, 1.0*inch, 0.8*inch, 0.8*inch, 0.8*inch]
    )
    
    t_style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1A237E')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D6D6D6')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]
    
    # Alternating row colors
    for r in range(1, len(table_data)):
        if r % 2 == 0:
            t_style.append(('BACKGROUND', (0, r), (-1, r), colors.HexColor('#FAFAFA')))
            
    prod_table.setStyle(TableStyle(t_style))
    story.append(prod_table)
    story.append(Spacer(1, 14))
    
    # 4. TOTALS & SUMMARY BOX
    totals_text = Paragraph(
        f"<font size=10><b>TOTAL SUMMARY:</b></font><br/>"
        f"Total Selected Designs: <b>{len(cart_items)}</b><br/>"
        f"Total Ordered Quantity: <b>{total_sets} Sets</b><br/>"
        f"Estimated Wholesale Amount: <b><font size=12 color='#1A237E'>₹{total_amount:,.2f}</font></b>",
        body_regular
    )
    
    terms_text = Paragraph(
        "<b>WHOLESALE ORDER TERMS:</b><br/>"
        "• All prices are wholesale estimates for shopkeepers & resellers.<br/>"
        "• Minimum order: 1 full size set per selected design.<br/>"
        "• Transportation & GST charges extra as applicable.<br/>"
        "• For instant order booking, contact <b>+91 9701515477</b>.",
        body_regular
    )
    
    summary_table = Table([[terms_text, totals_text]], colWidths=[4.2*inch, 2.8*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFF8E1')), # Light gold tint
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#FFE082')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # 5. FOOTER SIGNATURE
    footer_text = Paragraph(
        "<center><font size=8 color='#757575'>"
        "Thank you for choosing <b>AT SELECTION Hyderabad</b>! | This is a computer-generated wholesale quotation.<br/>"
        "📍 Shop: City Plaza Complex, Dewan Dewdi, Hyderabad | 📞 Call: +91 9701515477"
        "</font></center>",
        styles['Normal']
    )
    story.append(footer_text)
    
    doc.build(story)
    logger.info(f"Generated Wholesale Quotation PDF: {pdf_path}")
    return pdf_path
