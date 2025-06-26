# bt_pdf_export_improved.py - Export PDF amélioré des Bons de Travail - Desmarais & Gagné Inc.
# Version corrigée avec meilleure présentation et sans superposition de texte

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm, mm
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics import renderPDF
from datetime import datetime
import io
import logging

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BTToPDFExporter:
    """
    Générateur PDF amélioré pour les Bons de Travail DG Inc.
    Version corrigée sans superposition de texte
    """
    
    def __init__(self):
        self.page_width, self.page_height = A4
        self.margin = 2*cm
        self.content_width = self.page_width - 2*self.margin
        
        # Palette de couleurs DG Inc.
        self.dg_green = colors.Color(0, 169/255, 113/255)  # #00A971
        self.dg_green_dark = colors.Color(0, 103/255, 61/255)  # #00673D
        self.dg_green_light = colors.Color(220/255, 252/255, 231/255)  # #DCFCE7
        self.dg_green_ultra_light = colors.Color(240/255, 253/255, 244/255)  # #F0FDF4
        self.dg_gray = colors.Color(55/255, 65/255, 81/255)  # #374151
        self.dg_gray_light = colors.Color(156/255, 163/255, 175/255)  # #9CA3AF
        self.dg_gray_ultra_light = colors.Color(249/255, 250/255, 251/255)  # #F9FAFB
        self.dg_blue = colors.Color(59/255, 130/255, 246/255)  # #3B82F6
        self.dg_orange = colors.Color(245/255, 158/255, 11/255)  # #F59E0B
        self.dg_red = colors.Color(239/255, 68/255, 68/255)  # #EF4444
        
        # Styles personnalisés
        self.setup_styles()
    
    def setup_styles(self):
        """Configure les styles personnalisés DG Inc."""
        self.styles = getSampleStyleSheet()
        
        # Style titre principal
        self.styles.add(ParagraphStyle(
            name='DGTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.dg_green_dark,
            spaceAfter=20,
            spaceBefore=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Style section
        self.styles.add(ParagraphStyle(
            name='DGSection',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=colors.white,
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold',
            borderWidth=0,
            borderPadding=8,
            backColor=self.dg_green,
            alignment=TA_LEFT,
            leftIndent=5
        ))
        
        # Style sous-section
        self.styles.add(ParagraphStyle(
            name='DGSubSection',
            parent=self.styles['Heading4'],
            fontSize=12,
            textColor=self.dg_green_dark,
            spaceAfter=8,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        ))
        
        # Style normal
        self.styles.add(ParagraphStyle(
            name='DGNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.dg_gray,
            spaceAfter=6,
            fontName='Helvetica',
            alignment=TA_LEFT
        ))
        
        # Style important
        self.styles.add(ParagraphStyle(
            name='DGImportant',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=self.dg_green_dark,
            fontName='Helvetica-Bold',
            spaceAfter=8,
            leftIndent=5,
            borderWidth=1,
            borderColor=self.dg_green,
            borderPadding=6,
            backColor=self.dg_green_ultra_light
        ))

    def create_header_footer(self, canvas, doc):
        """Crée l'en-tête et le pied de page simplifiés"""
        canvas.saveState()
        
        # === EN-TÊTE SIMPLIFIÉ ===
        header_height = 60
        
        # Fond de l'en-tête
        canvas.setFillColor(self.dg_green_dark)
        canvas.rect(0, self.page_height - header_height, self.page_width, header_height, fill=1)
        
        # Logo DG simplifié
        logo_x = self.margin
        logo_y = self.page_height - header_height + 10
        
        canvas.setFillColor(colors.white)
        canvas.roundRect(logo_x, logo_y, 60, 35, 5, fill=1)
        canvas.setFillColor(self.dg_green_dark)
        canvas.setFont('Helvetica-Bold', 16)
        canvas.drawCentredString(logo_x + 30, logo_y + 15, "DG")
        
        # Nom de l'entreprise
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 18)
        canvas.drawString(logo_x + 80, logo_y + 25, "Desmarais & Gagne inc.")
        
        canvas.setFont('Helvetica', 10)
        canvas.drawString(logo_x + 80, logo_y + 10, "Solutions industrielles d'excellence")
        
        # Coordonnées alignées à droite
        canvas.setFont('Helvetica', 9)
        right_margin = self.page_width - self.margin
        canvas.drawRightString(right_margin, logo_y + 30, "565 rue Maisonneuve, Granby, QC J2G 3H5")
        canvas.drawRightString(right_margin, logo_y + 20, "Tel.: (450) 372-9630")
        canvas.drawRightString(right_margin, logo_y + 10, "Telec.: (450) 372-8122")
        
        # === PIED DE PAGE SIMPLIFIÉ ===
        footer_y = self.margin - 10
        
        # Ligne décorative
        canvas.setStrokeColor(self.dg_green)
        canvas.setLineWidth(1)
        canvas.line(self.margin, footer_y + 15, self.page_width - self.margin, footer_y + 15)
        
        # Informations du pied de page
        canvas.setFillColor(self.dg_gray)
        canvas.setFont('Helvetica', 8)
        
        # Date de génération
        date_text = f"Document genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')}"
        canvas.drawString(self.margin, footer_y, date_text)
        
        # Titre centré
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawCentredString(self.page_width/2, footer_y, "BON DE TRAVAIL - Systeme ERP DG Inc.")
        
        # Numéro de page
        page_text = f"Page {doc.page}"
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(self.page_width - self.margin, footer_y, page_text)
        
        canvas.restoreState()

    def export_bt_to_pdf(self, form_data):
        """
        Génère le PDF du Bon de Travail avec présentation améliorée
        """
        try:
            # Créer un buffer en mémoire
            buffer = io.BytesIO()
            
            # Créer le document PDF
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=self.margin,
                leftMargin=self.margin,
                topMargin=self.margin + 70,  # Espace pour l'en-tête
                bottomMargin=self.margin + 30  # Espace pour le pied de page
            )
            
            # Construire le contenu
            story = []
            
            # Titre principal
            story.append(Paragraph("BON DE TRAVAIL", self.styles['DGTitle']))
            story.append(Spacer(1, 15))
            
            # Informations générales
            self._add_general_info(story, form_data)
            story.append(Spacer(1, 15))
            
            # Tâches et opérations
            self._add_tasks_section(story, form_data)
            story.append(Spacer(1, 15))
            
            # Matériaux
            self._add_materials_section(story, form_data)
            story.append(Spacer(1, 15))
            
            # Instructions
            self._add_instructions_section(story, form_data)
            story.append(Spacer(1, 15))
            
            # Signatures
            self._add_signatures_section(story)
            
            # Construire le PDF
            doc.build(story, onFirstPage=self.create_header_footer, 
                     onLaterPages=self.create_header_footer)
            
            # Récupérer le contenu
            pdf_content = buffer.getvalue()
            buffer.close()
            
            logger.info(f"PDF ameliore genere avec succes pour BT {form_data.get('numero_document', 'N/A')}")
            return pdf_content
            
        except Exception as e:
            logger.error(f"Erreur generation PDF ameliore: {e}")
            raise e

    def _add_general_info(self, story, form_data):
        """Ajoute les informations générales avec badge de statut"""
        # Badge de statut en haut
        story.append(Paragraph("INFORMATIONS GENERALES", self.styles['DGSection']))
        story.append(Spacer(1, 8))
        
        # Tableau de statut simplifié
        numero = form_data.get('numero_document', 'N/A')
        priority = form_data.get('priority', 'NORMAL')
        statut = form_data.get('statut', 'BROUILLON')
        
        priority_display = self._format_priority_simple(priority)
        
        status_data = [
            ['Numero:', numero, 'Priorite:', priority_display, 'Statut:', statut]
        ]
        
        status_table = Table(status_data, colWidths=[2*cm, 3.5*cm, 2*cm, 2.5*cm, 2*cm, 3*cm])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.dg_green_light),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.dg_gray),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, self.dg_green),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        story.append(status_table)
        story.append(Spacer(1, 10))
        
        # Tableau principal des informations avec largeurs ajustées
        data = [
            ['Projet:', form_data.get('project_name', 'N/A')],
            ['Client:', form_data.get('client_name', 'N/A')],
            ['Charge de projet:', form_data.get('project_manager', 'Non assigne')],
            ['Date debut:', form_data.get('start_date', 'N/A')],
            ['Date fin prevue:', form_data.get('end_date', 'N/A')],
        ]
        
        table = Table(data, colWidths=[4*cm, 12*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), self.dg_green),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, self.dg_green_light),
            ('ROWBACKGROUNDS', (1, 0), (1, -1), [colors.white, self.dg_gray_ultra_light]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(table)

    def _add_tasks_section(self, story, form_data):
        """Ajoute la section des tâches avec largeurs optimisées"""
        story.append(Paragraph("TACHES ET OPERATIONS", self.styles['DGSection']))
        story.append(Spacer(1, 8))
        
        tasks = form_data.get('tasks', [])
        
        if not tasks or not any(t.get('operation') or t.get('description') for t in tasks):
            no_task_text = "Aucune tache definie pour ce bon de travail."
            story.append(Paragraph(no_task_text, self.styles['DGNormal']))
            return
        
        # En-têtes sans emojis
        headers = ['Operation', 'Description', 'Qte', 'H.Prev', 'H.Reel', 'Assigne', 'Fournisseur', 'Statut']
        data = [headers]
        
        total_planned = 0
        total_actual = 0
        
        for task in tasks:
            if task.get('operation') or task.get('description'):
                operation = task.get('operation', '')
                description = task.get('description', '')
                quantity = task.get('quantity', 1)
                planned_hours = task.get('planned_hours', 0.0)
                actual_hours = task.get('actual_hours', 0.0)
                assigned_to = task.get('assigned_to', '')
                fournisseur = task.get('fournisseur', '-- Interne --')
                status = self._format_status_simple(task.get('status', 'pending'))
                
                total_planned += planned_hours
                total_actual += actual_hours
                
                # Tronquer les textes pour éviter les débordements
                operation_display = operation[:15] + '...' if len(operation) > 15 else operation
                description_display = description[:20] + '...' if len(description) > 20 else description
                assigned_display = assigned_to[:12] + '...' if len(assigned_to) > 12 else assigned_to
                fournisseur_display = fournisseur[:15] + '...' if len(fournisseur) > 15 else fournisseur
                
                data.append([
                    operation_display,
                    description_display,
                    str(quantity),
                    f"{planned_hours:.1f}h",
                    f"{actual_hours:.1f}h",
                    assigned_display,
                    fournisseur_display,
                    status
                ])
        
        # Ligne de totaux
        data.append([
            'TOTAUX', '', '', 
            f"{total_planned:.1f}h", 
            f"{total_actual:.1f}h", 
            '', '', ''
        ])
        
        # Largeurs de colonnes optimisées pour A4
        col_widths = [2.8*cm, 3.2*cm, 1*cm, 1.2*cm, 1.2*cm, 2*cm, 2.5*cm, 1.8*cm]
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            # En-têtes
            ('BACKGROUND', (0, 0), (-1, 0), self.dg_green_dark),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Données
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('ALIGN', (2, 1), (4, -1), 'CENTER'),  # Colonnes numériques
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Ligne totaux
            ('BACKGROUND', (0, -1), (-1, -1), self.dg_green),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            
            # Grille
            ('GRID', (0, 0), (-1, -1), 0.5, self.dg_green_light),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, self.dg_gray_ultra_light]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(table)

    def _add_materials_section(self, story, form_data):
        """Ajoute la section des matériaux"""
        story.append(Paragraph("MATERIAUX ET OUTILS REQUIS", self.styles['DGSection']))
        story.append(Spacer(1, 8))
        
        materials = form_data.get('materials', [])
        
        if not materials or not any(m.get('name') for m in materials):
            no_material_text = "Aucun materiau ou outil specifie pour ce bon de travail."
            story.append(Paragraph(no_material_text, self.styles['DGNormal']))
            return
        
        # En-têtes simplifiés
        headers = ['Materiau/Outil', 'Description', 'Qte', 'Unite', 'Fournisseur', 'Disponibilite', 'Notes']
        data = [headers]
        
        for material in materials:
            if material.get('name'):
                name = material.get('name', '')
                description = material.get('description', '')
                quantity = material.get('quantity', 1.0)
                unit = material.get('unit', 'pcs')
                fournisseur = material.get('fournisseur', '-- Interne --')
                available = self._format_availability_simple(material.get('available', 'yes'))
                notes = material.get('notes', '')
                
                # Tronquer pour éviter les débordements
                name_display = name[:18] + '...' if len(name) > 18 else name
                description_display = description[:20] + '...' if len(description) > 20 else description
                fournisseur_display = fournisseur[:15] + '...' if len(fournisseur) > 15 else fournisseur
                notes_display = notes[:20] + '...' if len(notes) > 20 else notes
                
                data.append([
                    name_display,
                    description_display,
                    f"{quantity:.1f}",
                    unit,
                    fournisseur_display,
                    available,
                    notes_display
                ])
        
        # Largeurs optimisées
        col_widths = [3*cm, 3.5*cm, 1*cm, 1*cm, 2.5*cm, 2*cm, 2.5*cm]
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            # En-têtes
            ('BACKGROUND', (0, 0), (-1, 0), self.dg_blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Données
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (2, 1), (3, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Style
            ('GRID', (0, 0), (-1, -1), 0.5, self.dg_gray_light),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.dg_gray_ultra_light]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(table)

    def _add_instructions_section(self, story, form_data):
        """Ajoute la section des instructions"""
        story.append(Paragraph("INSTRUCTIONS ET NOTES", self.styles['DGSection']))
        story.append(Spacer(1, 8))
        
        # Instructions de travail
        work_instructions = form_data.get('work_instructions', '')
        if work_instructions:
            story.append(Paragraph("Instructions de travail:", self.styles['DGSubSection']))
            story.append(Paragraph(work_instructions, self.styles['DGNormal']))
            story.append(Spacer(1, 8))
        
        # Notes de sécurité
        safety_notes = form_data.get('safety_notes', '')
        if safety_notes:
            story.append(Paragraph("Notes de securite:", self.styles['DGSubSection']))
            story.append(Paragraph(safety_notes, self.styles['DGImportant']))
            story.append(Spacer(1, 8))
        
        # Exigences qualité
        quality_requirements = form_data.get('quality_requirements', '')
        if quality_requirements:
            story.append(Paragraph("Exigences qualite:", self.styles['DGSubSection']))
            story.append(Paragraph(quality_requirements, self.styles['DGNormal']))

    def _add_signatures_section(self, story):
        """Ajoute la section des signatures"""
        story.append(Spacer(1, 20))
        story.append(Paragraph("SIGNATURES ET APPROBATIONS", self.styles['DGSection']))
        story.append(Spacer(1, 10))
        
        # Tableau simplifié pour les signatures
        sig_data = [
            ['Prepare par:', '', 'Date:', '', 'Approuve par:', '', 'Date:', ''],
            ['', '', '', '', '', '', '', ''],
            ['Signature:', '', '', '', 'Signature:', '', '', ''],
            ['', '', '', '', '', '', '', ''],
        ]
        
        sig_table = Table(sig_data, colWidths=[2.5*cm, 3*cm, 1.5*cm, 2*cm, 2.5*cm, 3*cm, 1.5*cm, 2*cm])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, 0), self.dg_green_light),
            ('BACKGROUND', (0, 2), (-1, 2), self.dg_green_light),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.dg_gray),
            ('GRID', (0, 0), (-1, -1), 0.5, self.dg_green_light),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(sig_table)
        
        # Note légale
        story.append(Spacer(1, 15))
        legal_note = "Ce document constitue un engagement contractuel. Toute modification doit etre approuvee par ecrit."
        story.append(Paragraph(legal_note, self.styles['DGNormal']))

    def _format_priority_simple(self, priority):
        """Formate la priorité sans emojis"""
        priority_map = {
            'NORMAL': 'Normal',
            'URGENT': 'Urgent',
            'CRITIQUE': 'Critique'
        }
        return priority_map.get(priority, priority)

    def _format_status_simple(self, status):
        """Formate le statut sans emojis"""
        status_map = {
            'pending': 'En attente',
            'in-progress': 'En cours',
            'completed': 'Termine',
            'on-hold': 'En pause'
        }
        return status_map.get(status, status)

    def _format_availability_simple(self, availability):
        """Formate la disponibilité sans emojis"""
        avail_map = {
            'yes': 'Disponible',
            'no': 'Non dispo',
            'partial': 'Partiel',
            'ordered': 'Commande'
        }
        return avail_map.get(availability, availability)


def export_bt_pdf_streamlit(form_data):
    """Interface Streamlit pour l'export PDF amélioré"""
    try:
        # Créer l'exporteur
        exporter = BTToPDFExporter()
        
        # Générer le PDF
        with st.spinner("Generation du PDF en cours..."):
            pdf_content = exporter.export_bt_to_pdf(form_data)
        
        # Nom du fichier
        numero_document = form_data.get('numero_document', 'BT')
        filename = f"BT_{numero_document}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Bouton de téléchargement
        st.download_button(
            label="Telecharger le PDF",
            data=pdf_content,
            file_name=filename,
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        
        st.success(f"PDF genere avec succes ! **{filename}**")
        
        # Statistiques
        tasks_count = len([t for t in form_data.get('tasks', []) if t.get('operation') or t.get('description')])
        materials_count = len([m for m in form_data.get('materials', []) if m.get('name')])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Taches", tasks_count)
        with col2:
            st.metric("Materiaux", materials_count)
        with col3:
            st.metric("Taille", f"{len(pdf_content):,} bytes")
        
        return True
        
    except Exception as e:
        st.error(f"Erreur lors de la generation du PDF: {e}")
        logger.error(f"Erreur export PDF: {e}")
        return False


# Test avec données simplifiées
if __name__ == "__main__":
    sample_data = {
        'numero_document': 'BT-2025-003',
        'project_name': 'Projet Test',
        'client_name': 'Client Test',
        'project_manager': 'Manager Test',
        'priority': 'NORMAL',
        'start_date': '2025-06-26',
        'end_date': '2025-07-10',
        'statut': 'VALIDÉ',
        'work_instructions': 'Instructions de travail test.',
        'safety_notes': 'Notes de sécurité importantes.',
        'quality_requirements': 'Exigences qualité standards.',
        'tasks': [
            {
                'operation': 'Operation 1',
                'description': 'Description 1',
                'quantity': 1,
                'planned_hours': 5.0,
                'actual_hours': 4.5,
                'assigned_to': 'Technicien 1',
                'fournisseur': '-- Interne --',
                'status': 'completed'
            }
        ],
        'materials': [
            {
                'name': 'Materiau 1',
                'description': 'Description materiau',
                'quantity': 10.0,
                'unit': 'pcs',
                'fournisseur': 'Fournisseur Test',
                'available': 'yes',
                'notes': 'Notes test'
            }
        ]
    }
    
    try:
        exporter = BTToPDFExporter()
        pdf_content = exporter.export_bt_to_pdf(sample_data)
        
        with open('test_bt_ameliore.pdf', 'wb') as f:
            f.write(pdf_content)
        
        print("PDF ameliore genere: test_bt_ameliore.pdf")
        print(f"Taille: {len(pdf_content):,} bytes")
        
    except Exception as e:
        print(f"Erreur: {e}")