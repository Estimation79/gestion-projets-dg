import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from datetime import datetime
import io
import logging

logger = logging.getLogger(__name__)

# Couleurs DG Inc.
DG_PRIMARY = colors.Color(0, 169/255, 113/255)      # #00A971
DG_PRIMARY_DARK = colors.Color(0, 103/255, 61/255)  # #00673D
DG_LIGHT_GREEN = colors.Color(220/255, 252/255, 231/255)  # #DCFCE7
DG_GRAY = colors.Color(55/255, 65/255, 81/255)      # #374151
DG_LIGHT_GRAY = colors.Color(107/255, 114/255, 128/255)  # #6B7280

class BTPDFGenerator:
    """Générateur de PDF compact pour les Bons de Travail"""
    
    def __init__(self):
        self.page_width = A4[0]  # 595.28 points
        self.page_height = A4[1] # 841.89 points
        self.margin = 20  # MARGE MINIMALE pour maximiser l'espace
        self.content_width = self.page_width - 2 * self.margin  # ~555 points disponibles
        
        # LARGEUR UNIFORME POUR TOUS LES TABLEAUX
        self.table_width = self.content_width - 10  # Largeur standard pour tous
        
        # Styles uniformisés
        self.styles = getSampleStyleSheet()
        self._create_compact_styles()
    
    def _create_compact_styles(self):
        """Créer des styles ultra-compacts avec hauteur de texte réduite"""
        
        # COMPACITÉ MAXIMALE : Tailles réduites pour tout
        CONTENT_FONT_SIZE = 7   # Réduit de 9 à 7
        SECTION_FONT_SIZE = 10  # Réduit de 12 à 10
        
        # Style titre principal - plus compact
        self.styles.add(ParagraphStyle(
            name='DGTitle',
            parent=self.styles['Heading1'],
            fontSize=20,  # Réduit de 22 à 20
            textColor=DG_PRIMARY_DARK,
            spaceAfter=12,  # Réduit de 18 à 12
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=22  # Réduit de 26 à 22
        ))
        
        # Style section - plus compact
        self.styles.add(ParagraphStyle(
            name='DGSection',
            parent=self.styles['Heading3'],
            fontSize=SECTION_FONT_SIZE,  # Réduit de 12 à 10
            textColor=DG_PRIMARY_DARK,
            spaceAfter=6,   # Réduit de 8 à 6
            spaceBefore=8,  # Réduit de 12 à 8
            fontName='Helvetica-Bold',
            leading=12  # Réduit de 16 à 12
        ))
        
        # Style normal DG - ultra compact
        self.styles.add(ParagraphStyle(
            name='DGNormal',
            parent=self.styles['Normal'],
            fontSize=CONTENT_FONT_SIZE,  # 7pt au lieu de 9pt
            textColor=DG_GRAY,
            spaceAfter=2,  # Réduit de 4 à 2
            fontName='Helvetica',
            leading=9   # Réduit de 12 à 9
        ))
        
        # Style info importante - ultra compact
        self.styles.add(ParagraphStyle(
            name='DGImportant',
            parent=self.styles['Normal'],
            fontSize=CONTENT_FONT_SIZE,  # 7pt au lieu de 9pt
            textColor=DG_PRIMARY_DARK,
            fontName='Helvetica-Bold',
            spaceAfter=2,  # Réduit de 4 à 2
            leading=9   # Réduit de 12 à 9
        ))
        
        # Style petite info - plus petit
        self.styles.add(ParagraphStyle(
            name='DGSmall',
            parent=self.styles['Normal'],
            fontSize=6,  # Réduit de 8 à 6
            textColor=DG_LIGHT_GRAY,
            fontName='Helvetica',
            leading=8   # Réduit de 10 à 8
        ))
    
    def _get_compact_table_style(self, has_header=True):
        """Style de tableau ultra-compact avec bordures fines"""
        base_style = [
            # Bordures FINES et uniformes - Réduit de 1 à 0.5pt
            ('GRID', (0, 0), (-1, -1), 0.5, DG_GRAY),  # Grille fine 0.5pt
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, DG_GRAY),
            ('LINEBEFORE', (0, 0), (-1, -1), 0.5, DG_GRAY),
            ('LINEAFTER', (0, 0), (-1, -1), 0.5, DG_GRAY),
            ('LINEABOVE', (0, 0), (-1, -1), 0.5, DG_GRAY),
            
            # Polices COMPACTES
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),  # Réduit de 8 à 7
            
            # Alignement et espacement ULTRA-COMPACTS
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),    # Réduit de 4 à 2
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2), # Réduit de 4 à 2
            ('LEFTPADDING', (0, 0), (-1, -1), 2),   # Réduit de 3 à 2
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),  # Réduit de 3 à 2
            
            # Hauteur uniforme RÉDUITE
            ('ROWHEIGHT', (0, 0), (-1, -1), 16),    # Réduit de 20 à 16
        ]
        
        # Style spécial pour en-tête si présent
        if has_header:
            header_style = [
                ('BACKGROUND', (0, 0), (-1, 0), DG_PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),  # Réduit de 8 à 7
                ('LINEBELOW', (0, 0), (-1, 0), 1, DG_PRIMARY),  # Ligne sous en-tête
            ]
            base_style.extend(header_style)
            
            # Fond alterné pour le contenu (après en-tête)
            base_style.append(('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, DG_LIGHT_GREEN]))
        else:
            # Fond blanc pour tableaux sans en-tête
            base_style.append(('BACKGROUND', (0, 0), (-1, -1), colors.white))
        
        return base_style
    
    def _create_header_footer(self, canvas, doc):
        """Créer l'en-tête et le pied de page - VERSION ULTRA COMPACTE"""
        canvas.saveState()
        
        # En-tête ultra compact
        canvas.setFillColor(DG_PRIMARY)
        canvas.rect(self.margin, self.page_height - 60, 45, 20, fill=1, stroke=0)  # Plus petit
        
        # Logo texte plus petit
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 12)  # Réduit de 14 à 12
        text_width = canvas.stringWidth("DG", 'Helvetica-Bold', 12)
        canvas.drawString(self.margin + 22.5 - text_width/2, self.page_height - 54, "DG")
        
        # Nom de l'entreprise plus compact
        canvas.setFillColor(DG_PRIMARY_DARK)
        canvas.setFont('Helvetica-Bold', 14)  # Réduit de 16 à 14
        canvas.drawString(self.margin + 55, self.page_height - 50, "Desmarais & Gagné inc.")
        
        # Coordonnées ultra compactes
        canvas.setFillColor(DG_GRAY)
        canvas.setFont('Helvetica', 7)  # Réduit de 8 à 7
        contact_info = [
            "565 rue Maisonneuve, Granby, QC J2G 3H5",
            "Tél.: (450) 372-9630 | Téléc.: (450) 372-8122",
            "www.dg-inc.com"
        ]
        
        y_contact = self.page_height - 55
        for line in contact_info:
            canvas.drawRightString(self.page_width - self.margin, y_contact, line)
            y_contact -= 8  # Réduit de 10 à 8
        
        # Ligne de séparation plus fine
        canvas.setStrokeColor(DG_PRIMARY)
        canvas.setLineWidth(0.5)  # Réduit de 1 à 0.5
        canvas.line(self.margin, self.page_height - 75, 
                   self.page_width - self.margin, self.page_height - 75)
        
        # Pied de page ultra compact
        canvas.setFillColor(DG_LIGHT_GRAY)
        canvas.setFont('Helvetica', 7)  # Réduit de 8 à 7
        
        date_impression = f"Imprimé le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
        canvas.drawString(self.margin, 20, date_impression)  # Réduit de 25 à 20
        
        page_num = f"Page {doc.page}"
        canvas.drawRightString(self.page_width - self.margin, 20, page_num)
        
        canvas.setStrokeColor(DG_PRIMARY)
        canvas.setLineWidth(0.5)  # Plus fine
        canvas.line(self.margin, 35, self.page_width - self.margin, 35)  # Réduit de 40 à 35
        
        canvas.restoreState()
    
    def _create_info_section(self, form_data):
        """Créer la section d'informations générales - VERSION COMPACTE"""
        elements = []
        
        # Titre du document
        title = Paragraph("BON DE TRAVAIL", self.styles['DGTitle'])
        elements.append(title)
        elements.append(Spacer(1, 10))  # Réduit de 15 à 10
        
        # Informations principales
        info_data = [
            ['N° Bon de Travail:', form_data.get('numero_document', 'N/A'), 
             'Date de création:', form_data.get('date_creation', datetime.now().strftime('%Y-%m-%d'))[:10]],
            ['Projet:', form_data.get('project_name', 'N/A'),
             'Client:', form_data.get('client_name', 'N/A')],
            ['Chargé de projet:', form_data.get('project_manager', 'Non assigné'),
             'Priorité:', self._get_priority_display(form_data.get('priority', 'NORMAL'))],
            ['Date début prévue:', form_data.get('start_date', 'N/A'), 
             'Date fin prévue:', form_data.get('end_date', 'N/A')]
        ]
        
        # Largeurs uniformes
        info_table = Table(info_data, colWidths=[
            self.table_width * 0.18,  # Étiquettes (18%)
            self.table_width * 0.32,  # Valeurs (32%)
            self.table_width * 0.18,  # Étiquettes (18%)
            self.table_width * 0.32   # Valeurs (32%)
        ], spaceAfter=0, spaceBefore=0)
        
        info_table.setStyle(TableStyle([
            # Couleurs spéciales pour section info
            ('BACKGROUND', (0, 0), (0, -1), DG_LIGHT_GREEN),
            ('BACKGROUND', (2, 0), (2, -1), DG_LIGHT_GREEN),
            ('TEXTCOLOR', (0, 0), (-1, -1), DG_GRAY),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ] + self._get_compact_table_style(has_header=False)))
        
        elements.append(info_table)
        elements.append(Spacer(1, 10))  # Réduit de 15 à 10
        
        return elements
    
    def _create_tasks_section(self, form_data):
        """Créer la section des tâches - VERSION ULTRA COMPACTE"""
        elements = []
        
        tasks = form_data.get('tasks', [])
        if not tasks or not any(task.get('operation') or task.get('description') for task in tasks):
            return elements
        
        # Titre de section
        section_title = Paragraph("TÂCHES ET OPÉRATIONS", self.styles['DGSection'])
        elements.append(section_title)
        elements.append(Spacer(1, 6))  # Réduit de 8 à 6
        
        # En-têtes optimisés
        headers = ['N°', 'Opération', 'Description', 'Qté', 'H.Prév', 'H.Réel', 'Assigné à', 'Fournisseur', 'Statut']
        
        # Données des tâches
        task_data = [headers]
        
        valid_tasks = [task for task in tasks if task.get('operation') or task.get('description')]
        
        for i, task in enumerate(valid_tasks, 1):
            operation = task.get('operation', '')
            description = task.get('description', '')
            quantity = str(task.get('quantity', 1))
            planned_hours = f"{task.get('planned_hours', 0):.1f}"
            actual_hours = f"{task.get('actual_hours', 0):.1f}"
            assigned_to = task.get('assigned_to', '')
            fournisseur = task.get('fournisseur', '-- Interne --')
            status = self._get_status_display(task.get('status', 'pending'))
            
            task_data.append([
                str(i), operation, description, quantity, 
                planned_hours, actual_hours, assigned_to, fournisseur, status
            ])
        
        if len(task_data) > 1:
            tasks_table = Table(task_data, colWidths=[
                18,   # N° - plus petit
                self.table_width * 0.23,  # Opération - 23%
                self.table_width * 0.23,  # Description - 23%
                22,   # Qté - plus petit
                28,   # H.Prév - plus petit
                28,   # H.Réel - plus petit
                self.table_width * 0.16,  # Assigné - 16%
                self.table_width * 0.18,  # Fournisseur - 18%
                self.table_width * 0.12   # Statut - 12%
            ])
            
            tasks_table.setStyle(TableStyle([
                # Alignements spéciaux pour tâches
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 1), (2, -1), 'LEFT'),     # Opération et description à gauche
                ('ALIGN', (6, 1), (7, -1), 'LEFT'),     # Assigné et fournisseur à gauche
            ] + self._get_compact_table_style(has_header=True)))
            
            elements.append(tasks_table)
            elements.append(Spacer(1, 6))  # Réduit de 10 à 6
            
            # Totaux ultra compacts
            total_planned = sum(task.get('planned_hours', 0) for task in valid_tasks)
            total_actual = sum(task.get('actual_hours', 0) for task in valid_tasks)
            internal_planned = sum(task.get('planned_hours', 0) for task in valid_tasks 
                                 if task.get('fournisseur') == '-- Interne --')
            external_planned = total_planned - internal_planned
            
            totals_text = f"""<b>TOTAUX:</b> H.prév: <b>{total_planned:.1f}h</b> (Int: {internal_planned:.1f}h, Ext: {external_planned:.1f}h) • H.réel: <b>{total_actual:.1f}h</b> • Tâches: <b>{len(valid_tasks)}</b>"""
            
            totals_para = Paragraph(totals_text, self.styles['DGImportant'])
            elements.append(totals_para)
            elements.append(Spacer(1, 8))  # Réduit de 12 à 8
        
        return elements
    
    def _create_materials_section(self, form_data):
        """Créer la section des matériaux - VERSION COMPACTE"""
        elements = []
        
        materials = form_data.get('materials', [])
        valid_materials = [mat for mat in materials if mat.get('name')]
        
        if not valid_materials:
            return elements
        
        # Titre de section
        section_title = Paragraph("MATÉRIAUX ET OUTILS REQUIS", self.styles['DGSection'])
        elements.append(section_title)
        elements.append(Spacer(1, 6))  # Réduit de 8 à 6
        
        # En-têtes optimisés
        headers = ['N°', 'Matériau/Outil', 'Description', 'Qté', 'Unité', 'Fournisseur', 'Disponibilité', 'Notes']
        
        # Données des matériaux
        material_data = [headers]
        
        for i, material in enumerate(valid_materials, 1):
            name = material.get('name', '')
            description = material.get('description', '')
            quantity = f"{material.get('quantity', 1):.1f}"
            unit = material.get('unit', 'pcs')
            fournisseur = material.get('fournisseur', '-- Interne --')
            available = self._get_availability_display(material.get('available', 'yes'))
            notes = material.get('notes', '')
            
            material_data.append([
                str(i), name, description, quantity, unit, fournisseur, available, notes
            ])
        
        # Largeurs compactes
        materials_table = Table(material_data, colWidths=[
            22,   # N° - plus petit
            self.table_width * 0.22,  # Matériau - 22%
            self.table_width * 0.25,  # Description - 25%
            30,   # Qté - plus petit
            30,   # Unité - plus petit
            self.table_width * 0.20,  # Fournisseur - 20%
            self.table_width * 0.15,  # Disponibilité - 15%
            self.table_width * 0.13   # Notes - 13%
        ])
        
        materials_table.setStyle(TableStyle([
            # Alignements spéciaux pour matériaux
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (2, -1), 'LEFT'),     # Nom et description à gauche
            ('ALIGN', (5, 1), (7, -1), 'LEFT'),     # Fournisseur et notes à gauche
        ] + self._get_compact_table_style(has_header=True)))
        
        elements.append(materials_table)
        elements.append(Spacer(1, 8))  # Réduit de 12 à 8
        
        return elements
    
    def _create_instructions_section(self, form_data):
        """Créer la section des instructions - VERSION ULTRA COMPACTE"""
        elements = []
        
        work_instructions = form_data.get('work_instructions', '').strip()
        safety_notes = form_data.get('safety_notes', '').strip()
        quality_requirements = form_data.get('quality_requirements', '').strip()
        
        if not any([work_instructions, safety_notes, quality_requirements]):
            return elements
        
        # Titre de section
        section_title = Paragraph("INSTRUCTIONS ET NOTES", self.styles['DGSection'])
        elements.append(section_title)
        elements.append(Spacer(1, 4))  # Réduit de 6 à 4
        
        # Instructions ultra compactes
        if work_instructions:
            work_title = Paragraph("<b>Instructions de travail:</b>", self.styles['DGImportant'])
            elements.append(work_title)
            work_text = Paragraph(work_instructions, self.styles['DGNormal'])
            elements.append(work_text)
            elements.append(Spacer(1, 4))  # Réduit de 6 à 4
        
        if safety_notes:
            safety_title = Paragraph("<b>⚠️ Notes de sécurité:</b>", self.styles['DGImportant'])
            elements.append(safety_title)
            safety_text = Paragraph(safety_notes, self.styles['DGNormal'])
            elements.append(safety_text)
            elements.append(Spacer(1, 4))  # Réduit de 6 à 4
        
        if quality_requirements:
            quality_title = Paragraph("<b>🎯 Exigences qualité:</b>", self.styles['DGImportant'])
            elements.append(quality_title)
            quality_text = Paragraph(quality_requirements, self.styles['DGNormal'])
            elements.append(quality_text)
            elements.append(Spacer(1, 6))  # Réduit de 8 à 6
        
        return elements
    
    def _create_signatures_section(self):
        """Créer la section des signatures - VERSION COMPACTE"""
        elements = []
        
        # Titre de section
        section_title = Paragraph("VALIDATIONS ET SIGNATURES", self.styles['DGSection'])
        elements.append(section_title)
        elements.append(Spacer(1, 4))  # Réduit de 6 à 4
        
        # Tableau des signatures compact
        signature_data = [
            ['Rôle', 'Nom', 'Signature', 'Date'],
            ['Chargé de projet', '', '', ''],
            ['Superviseur production', '', '', ''],
            ['Contrôle qualité', '', '', ''],
            ['Client (si requis)', '', '', '']
        ]
        
        # Largeurs compactes
        signatures_table = Table(signature_data, colWidths=[
            self.table_width * 0.30,  # Rôle (30%)
            self.table_width * 0.25,  # Nom (25%)
            self.table_width * 0.30,  # Signature (30%)
            self.table_width * 0.15   # Date (15%)
        ])
        
        signatures_table.setStyle(TableStyle([
            # Alignements spéciaux pour signatures
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (1, -1), 'LEFT'),     # Rôle et nom à gauche
            ('ROWHEIGHT', (0, 1), (-1, -1), 20),    # Hauteur réduite pour signatures
        ] + self._get_compact_table_style(has_header=True)))
        
        elements.append(signatures_table)
        elements.append(Spacer(1, 10))  # Réduit de 15 à 10
        
        return elements
    
    def _get_priority_display(self, priority):
        """Convertir la priorité en affichage"""
        priority_map = {
            'NORMAL': '🟢 Normal',
            'URGENT': '🟡 Urgent',
            'CRITIQUE': '🔴 Critique'
        }
        return priority_map.get(priority, priority)
    
    def _get_status_display(self, status):
        """Convertir le statut en affichage"""
        status_map = {
            'pending': 'En attente',
            'in-progress': 'En cours',
            'completed': 'Terminé',
            'on-hold': 'En pause'
        }
        return status_map.get(status, status)
    
    def _get_availability_display(self, availability):
        """Convertir la disponibilité en affichage"""
        availability_map = {
            'yes': '✅ Disponible',
            'no': '❌ Non dispo',
            'partial': '⚠️ Partiel',
            'ordered': '📦 Commandé'
        }
        return availability_map.get(availability, availability)
    
    def generate_pdf(self, form_data):
        """Générer le PDF complet - VERSION ULTRA COMPACTE"""
        # Créer un buffer pour le PDF
        buffer = io.BytesIO()
        
        # Document avec marges optimisées
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=85,     # En-tête plus compact (réduit de 100 à 85)
            bottomMargin=50   # Pied de page plus compact (réduit de 55 à 50)
        )
        
        # Éléments du document
        elements = []
        
        # Ajouter toutes les sections optimisées
        elements.extend(self._create_info_section(form_data))
        elements.extend(self._create_tasks_section(form_data))
        elements.extend(self._create_materials_section(form_data))
        elements.extend(self._create_instructions_section(form_data))
        elements.extend(self._create_signatures_section())
        
        # Générer le PDF
        doc.build(elements, onFirstPage=self._create_header_footer, 
                 onLaterPages=self._create_header_footer)
        
        # Retourner le buffer
        buffer.seek(0)
        return buffer

def export_bt_pdf_streamlit(form_data):
    """
    Fonction principale d'export PDF pour Streamlit - VERSION ULTRA COMPACTE
    """
    try:
        # Validation des données minimales
        if not form_data.get('numero_document'):
            st.error("❌ Numéro de document requis pour l'export PDF")
            return
        
        if not form_data.get('project_name'):
            st.error("❌ Nom du projet requis pour l'export PDF")
            return
        
        # Créer le générateur PDF compact
        pdf_generator = BTPDFGenerator()
        
        # Générer le PDF
        with st.spinner("📄 Génération du PDF ultra-compact..."):
            pdf_buffer = pdf_generator.generate_pdf(form_data)
        
        # Nom du fichier
        numero_doc = form_data.get('numero_document', 'BT')
        projet = form_data.get('project_name', 'Projet')[:30]
        projet_clean = "".join(c for c in projet if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"BT_{numero_doc}_{projet_clean}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # Bouton de téléchargement
        st.download_button(
            label="📥 Télécharger le PDF Ultra-Compact",
            data=pdf_buffer.getvalue(),
            file_name=filename,
            mime="application/pdf",
            type="primary",
            help=f"Télécharger le bon de travail {numero_doc} - Version ultra-compacte"
        )
        
        st.success(f"✅ PDF ultra-compact généré avec succès ! Fichier: {filename}")
        
        # Informations sur les améliorations COMPACTES
        st.info("""
        🎯 **Version Ultra-Compacte - Améliorations :**
        • ✅ **Hauteur de texte réduite** : Police 7pt au lieu de 9pt (22% plus compact)
        • ✅ **Bordures fines** : Cadres 0.5pt au lieu de 1pt (look plus fin)
        • ✅ **Hauteur de lignes** : 16pt au lieu de 20pt (20% plus compact)
        • ✅ **Padding réduit** : 2pt au lieu de 4pt (espacement minimal)
        • ✅ **En-tête compact** : Hauteur réduite de 15pt
        • ✅ **Espacement uniforme** : Cohérence parfaite entre toutes les sections
        """)
        
        # Statistiques du PDF
        tasks_count = len([t for t in form_data.get('tasks', []) if t.get('operation')])
        materials_count = len([m for m in form_data.get('materials', []) if m.get('name')])
        total_hours = sum(task.get('planned_hours', 0) for task in form_data.get('tasks', []))
        
        st.info(f"""
        📊 **Contenu du PDF Ultra-Compact :**
        - **Bon de Travail:** {numero_doc}
        - **Projet:** {form_data.get('project_name', 'N/A')}
        - **Tâches:** {tasks_count} opérations ({total_hours:.1f}h prévues)
        - **Matériaux:** {materials_count} éléments
        - **Compacité:** Hauteur de ligne 16pt, police 7pt, bordures 0.5pt
        - **Uniformité:** Espacement standardisé dans toutes les sections
        """)
        
    except Exception as e:
        logger.error(f"Erreur génération PDF compact: {e}")
        st.error(f"❌ Erreur lors de la génération du PDF: {str(e)}")
        st.info("💡 Vérifiez que ReportLab est installé: `pip install reportlab`")

def test_pdf_generation():
    """Fonction de test pour la version ultra-compacte"""
    test_data = {
        'numero_document': 'BT-2025-001',
        'project_name': 'ATTACHE DE SERRE 10" (T DE SERRE) - Projet Complet de Fabrication',
        'client_name': 'Doucet Machineries Agricoles Inc.',
        'project_manager': 'Jovick Desmarais - Ingénieur Senior',
        'priority': 'NORMAL',
        'start_date': '2025-07-04',
        'end_date': '2025-07-11',
        'work_instructions': 'Instructions détaillées pour la fabrication des attaches de serre selon les spécifications techniques du client avec contrôle qualité rigoureux.',
        'safety_notes': 'Port des EPI obligatoire en tout temps. Attention particulière lors des opérations de soudage robotisé. Ventilation adéquate requise.',
        'quality_requirements': 'Contrôle dimensionnel selon ISO 9001. Vérification de la résistance à la traction selon normes canadiennes.',
        'tasks': [
            {
                'operation': '1001 - Temps Machine',
                'description': 'Préparation et réglage machine CNC',
                'quantity': 1,
                'planned_hours': 1.0,
                'actual_hours': 0.0,
                'assigned_to': 'Technicien CNC',
                'fournisseur': '-- Interne --',
                'status': 'pending'
            },
            {
                'operation': '1000 - Génération Programmation',
                'description': 'Programmation complète avec simulation',
                'quantity': 1,
                'planned_hours': 4.7,
                'actual_hours': 0.0,
                'assigned_to': 'Programmeur CNC',
                'fournisseur': '-- Interne --',
                'status': 'pending'
            },
            {
                'operation': '1004 - Scie Métal',
                'description': 'Découpe des barres selon plan',
                'quantity': 1,
                'planned_hours': 9.0,
                'actual_hours': 0.0,
                'assigned_to': 'Opérateur Scie',
                'fournisseur': '-- Interne --',
                'status': 'pending'
            },
            {
                'operation': '1012 - Robot Soudage',
                'description': 'Soudage robotisé des attaches',
                'quantity': 1,
                'planned_hours': 5.7,
                'actual_hours': 0.0,
                'assigned_to': 'Soudeur Robot',
                'fournisseur': '-- Interne --',
                'status': 'pending'
            }
        ],
        'materials': [
            {
                'name': 'Acier galvanisé haute résistance certifié',
                'description': 'Barre rectangulaire 40x20x3mm, galvanisation à chaud selon norme ASTM A653',
                'quantity': 12.5,
                'unit': 'm',
                'fournisseur': 'Métallurgie Québec Inc. Fournisseur Certifié',
                'available': 'yes',
                'notes': 'Stock vérifié, qualité contrôlée, certificats disponibles'
            },
            {
                'name': 'Électrodes soudage spécialisées haute performance',
                'description': 'Fil ER70S-6 diamètre 1.2mm pour soudage robotisé haute précision',
                'quantity': 5.0,
                'unit': 'kg',
                'fournisseur': 'Soudage Spécialisé Ltée Division Industrielle',
                'available': 'ordered',
                'notes': 'Livraison confirmée pour demain matin 8h00'
            }
        ]
    }
    
    return test_data

if __name__ == "__main__":
    # Test de la version ultra-compacte
    test_data = test_pdf_generation()
    generator = BTPDFGenerator()
    pdf_buffer = generator.generate_pdf(test_data)
    
    with open("test_bt_ultra_compact.pdf", "wb") as f:
        f.write(pdf_buffer.getvalue())
    
    print("✅ PDF ultra-compact généré: test_bt_ultra_compact.pdf")
    print("🎯 Hauteur de texte réduite, bordures fines, espacement uniforme !")
    print("📏 Police 7pt, hauteur de ligne 16pt, bordures 0.5pt pour un look épuré !")
