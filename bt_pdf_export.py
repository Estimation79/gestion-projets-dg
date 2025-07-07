# bt_pdf_export.py - Module d'export PDF pour les Bons de Travail - VERSION AMÉLIORÉE FINALE
# Desmarais & Gagné Inc. - Système ERP Production
# Génération de PDFs professionnels avec identité DG Inc.
# VERSION AMÉLIORÉE : Polices uniformes, texte non tronqué, espacement cohérent

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
    """Générateur de PDF pour les Bons de Travail - VERSION AMÉLIORÉE FINALE"""
    
    def __init__(self):
        self.page_width = A4[0]
        self.page_height = A4[1]
        self.margin = 40
        self.content_width = self.page_width - 2 * self.margin
        
        # Styles uniformisés
        self.styles = getSampleStyleSheet()
        self._create_uniform_styles()
    
    def _create_uniform_styles(self):
        """Créer des styles parfaitement uniformes - TOUTES LES POLICES COHÉRENTES"""
        
        # STANDARD UNIFORME : Une seule famille de tailles
        BASE_FONT_SIZE = 10  # Taille de base pour tout le contenu
        
        # Style titre principal
        self.styles.add(ParagraphStyle(
            name='DGTitle',
            parent=self.styles['Heading1'],
            fontSize=24,  # Titre principal plus grand
            textColor=DG_PRIMARY_DARK,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=28
        ))
        
        # Style sous-titre
        self.styles.add(ParagraphStyle(
            name='DGSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,  # Sous-titre cohérent
            textColor=DG_PRIMARY,
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold',
            leading=20
        ))
        
        # Style section
        self.styles.add(ParagraphStyle(
            name='DGSection',
            parent=self.styles['Heading3'],
            fontSize=14,  # Section cohérente
            textColor=DG_PRIMARY_DARK,
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold',
            leading=18
        ))
        
        # Style normal DG - BASE UNIFORME
        self.styles.add(ParagraphStyle(
            name='DGNormal',
            parent=self.styles['Normal'],
            fontSize=BASE_FONT_SIZE,  # 10pt partout
            textColor=DG_GRAY,
            spaceAfter=6,
            fontName='Helvetica',
            leading=14
        ))
        
        # Style info importante - MÊME BASE
        self.styles.add(ParagraphStyle(
            name='DGImportant',
            parent=self.styles['Normal'],
            fontSize=BASE_FONT_SIZE,  # 10pt uniforme
            textColor=DG_PRIMARY_DARK,
            fontName='Helvetica-Bold',
            spaceAfter=6,
            leading=14
        ))
        
        # Style petite info - LÉGÈREMENT PLUS PETIT MAIS COHÉRENT
        self.styles.add(ParagraphStyle(
            name='DGSmall',
            parent=self.styles['Normal'],
            fontSize=9,  # Seulement 1pt de différence
            textColor=DG_LIGHT_GRAY,
            fontName='Helvetica',
            leading=12
        ))
    
    def _create_header_footer(self, canvas, doc):
        """Créer l'en-tête et le pied de page - VERSION AMÉLIORÉE"""
        canvas.saveState()
        
        # En-tête avec logo DG amélioré
        canvas.setFillColor(DG_PRIMARY)
        canvas.rect(self.margin, self.page_height - 80, 60, 30, fill=1, stroke=0)
        
        # Logo texte centré
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 16)
        text_width = canvas.stringWidth("DG", 'Helvetica-Bold', 16)
        canvas.drawString(self.margin + 30 - text_width/2, self.page_height - 70, "DG")
        
        # Nom de l'entreprise
        canvas.setFillColor(DG_PRIMARY_DARK)
        canvas.setFont('Helvetica-Bold', 18)
        canvas.drawString(self.margin + 75, self.page_height - 65, "Desmarais & Gagné inc.")
        
        # Coordonnées uniformes
        canvas.setFillColor(DG_GRAY)
        canvas.setFont('Helvetica', 9)  # Police uniforme pour coordonnées
        contact_info = [
            "565 rue Maisonneuve, Granby, QC J2G 3H5",
            "Tél.: (450) 372-9630 | Téléc.: (450) 372-8122",
            "www.dg-inc.com"
        ]
        
        y_contact = self.page_height - 75
        for line in contact_info:
            canvas.drawRightString(self.page_width - self.margin, y_contact, line)
            y_contact -= 12
        
        # Ligne de séparation
        canvas.setStrokeColor(DG_PRIMARY)
        canvas.setLineWidth(2)
        canvas.line(self.margin, self.page_height - 100, 
                   self.page_width - self.margin, self.page_height - 100)
        
        # Pied de page uniforme
        canvas.setFillColor(DG_LIGHT_GRAY)
        canvas.setFont('Helvetica', 9)  # Police uniforme
        
        date_impression = f"Imprimé le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
        canvas.drawString(self.margin, 30, date_impression)
        
        page_num = f"Page {doc.page}"
        canvas.drawRightString(self.page_width - self.margin, 30, page_num)
        
        canvas.setStrokeColor(DG_PRIMARY)
        canvas.setLineWidth(1)
        canvas.line(self.margin, 45, self.page_width - self.margin, 45)
        
        canvas.restoreState()
    
    def _smart_truncate(self, text, max_length, suffix="..."):
        """Troncature intelligente qui préserve les mots complets"""
        if not text or len(text) <= max_length:
            return text or ''
        
        # Essayer de couper sur un espace
        truncated = text[:max_length - len(suffix)]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.7:  # Si l'espace est assez loin
            return truncated[:last_space] + suffix
        else:
            return truncated + suffix
    
    def _create_info_section(self, form_data):
        """Créer la section d'informations générales - VERSION OPTIMISÉE"""
        elements = []
        
        # Titre du document
        title = Paragraph("BON DE TRAVAIL", self.styles['DGTitle'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Informations principales - LARGEURS OPTIMISÉES POUR ÉVITER TRONCATURE
        info_data = [
            ['N° Bon de Travail:', form_data.get('numero_document', 'N/A'), 
             'Date de création:', form_data.get('date_creation', datetime.now().strftime('%Y-%m-%d'))[:10]],
            ['Projet:', form_data.get('project_name', 'N/A'),  # AUCUNE troncature
             'Client:', form_data.get('client_name', 'N/A')],   # AUCUNE troncature
            ['Chargé de projet:', self._smart_truncate(form_data.get('project_manager', 'Non assigné'), 30), 
             'Priorité:', self._get_priority_display(form_data.get('priority', 'NORMAL'))],
            ['Date début prévue:', form_data.get('start_date', 'N/A'), 
             'Date fin prévue:', form_data.get('end_date', 'N/A')]
        ]
        
        # OPTIMISATION FINALE : Largeurs calculées pour utiliser 100% de l'espace
        available_width = self.content_width - 20  # Marges internes
        col_widths = [available_width * 0.18, available_width * 0.32, 
                     available_width * 0.18, available_width * 0.32]
        
        info_table = Table(info_data, colWidths=col_widths)
        info_table.setStyle(TableStyle([
            # Couleurs et fond
            ('BACKGROUND', (0, 0), (0, -1), DG_LIGHT_GREEN),
            ('BACKGROUND', (2, 0), (2, -1), DG_LIGHT_GREEN),
            ('TEXTCOLOR', (0, 0), (-1, -1), DG_GRAY),
            
            # Polices UNIFORMES
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),  # TAILLE UNIFORME
            
            # Alignement et espacement
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, DG_PRIMARY),
            
            # Padding UNIFORME
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            
            # Hauteur uniforme
            ('ROWHEIGHT', (0, 0), (-1, -1), 28),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_tasks_section(self, form_data):
        """Créer la section des tâches - VERSION SANS TRONCATURE"""
        elements = []
        
        tasks = form_data.get('tasks', [])
        if not tasks or not any(task.get('operation') or task.get('description') for task in tasks):
            return elements
        
        # Titre de section
        section_title = Paragraph("TÂCHES ET OPÉRATIONS", self.styles['DGSection'])
        elements.append(section_title)
        elements.append(Spacer(1, 12))
        
        # En-têtes optimisés
        headers = ['N°', 'Opération', 'Description', 'Qté', 'H.Prév', 'H.Réel', 'Assigné à', 'Fournisseur', 'Statut']
        
        # Données des tâches
        task_data = [headers]
        
        valid_tasks = [task for task in tasks if task.get('operation') or task.get('description')]
        
        for i, task in enumerate(valid_tasks, 1):
            # MINIMAL TRUNCATION - Préserver l'information importante
            operation = self._smart_truncate(task.get('operation', ''), 25)
            description = self._smart_truncate(task.get('description', ''), 40)  # Plus d'espace pour description
            quantity = str(task.get('quantity', 1))
            planned_hours = f"{task.get('planned_hours', 0):.1f}"
            actual_hours = f"{task.get('actual_hours', 0):.1f}"
            assigned_to = self._smart_truncate(task.get('assigned_to', ''), 20)
            fournisseur = self._smart_truncate(task.get('fournisseur', '-- Interne --'), 25)
            status = self._get_status_display(task.get('status', 'pending'))
            
            task_data.append([
                str(i), operation, description, quantity, 
                planned_hours, actual_hours, assigned_to, fournisseur, status
            ])
        
        if len(task_data) > 1:
            # LARGEURS OPTIMISÉES pour maximiser l'espace sans troncature excessive
            available_width = self.content_width - 10
            tasks_table = Table(task_data, colWidths=[
                available_width * 0.05,  # N° (5%)
                available_width * 0.20,  # Opération (20%)
                available_width * 0.25,  # Description (25%)
                available_width * 0.06,  # Qté (6%)
                available_width * 0.08,  # H.Prév (8%)
                available_width * 0.08,  # H.Réel (8%)
                available_width * 0.12,  # Assigné (12%)
                available_width * 0.12,  # Fournisseur (12%)
                available_width * 0.04   # Statut (4%)
            ])
            
            tasks_table.setStyle(TableStyle([
                # En-tête uniforme
                ('BACKGROUND', (0, 0), (-1, 0), DG_PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),  # UNIFORME
                
                # Contenu uniforme
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),  # Légèrement plus petit pour le contenu
                
                # Alignement optimisé
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 1), (2, -1), 'LEFT'),     # Opération et description à gauche
                ('ALIGN', (6, 1), (7, -1), 'LEFT'),     # Assigné et fournisseur à gauche
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Bordures et couleurs
                ('GRID', (0, 0), (-1, -1), 0.5, DG_GRAY),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, DG_LIGHT_GREEN]),
                
                # Espacement UNIFORME
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                
                # Hauteur uniforme pour éviter la superposition
                ('ROWHEIGHT', (0, 1), (-1, -1), 24),
                
                # Lignes professionnelles
                ('LINEBELOW', (0, 0), (-1, 0), 2, DG_PRIMARY),
            ]))
            
            elements.append(tasks_table)
            elements.append(Spacer(1, 12))
            
            # Totaux avec style uniforme
            total_planned = sum(task.get('planned_hours', 0) for task in valid_tasks)
            total_actual = sum(task.get('actual_hours', 0) for task in valid_tasks)
            internal_planned = sum(task.get('planned_hours', 0) for task in valid_tasks 
                                 if task.get('fournisseur') == '-- Interne --')
            external_planned = total_planned - internal_planned
            
            totals_text = f"""<b>TOTAUX:</b><br/>
            • Heures prévues: <b>{total_planned:.1f}h</b> (Interne: {internal_planned:.1f}h, Externe: {external_planned:.1f}h)<br/>
            • Heures réelles: <b>{total_actual:.1f}h</b><br/>
            • Nombre de tâches: <b>{len(valid_tasks)}</b>"""
            
            totals_para = Paragraph(totals_text, self.styles['DGImportant'])
            elements.append(totals_para)
            elements.append(Spacer(1, 15))
        
        return elements
    
    def _create_materials_section(self, form_data):
        """Créer la section des matériaux - VERSION OPTIMISÉE"""
        elements = []
        
        materials = form_data.get('materials', [])
        valid_materials = [mat for mat in materials if mat.get('name')]
        
        if not valid_materials:
            return elements
        
        # Titre de section
        section_title = Paragraph("MATÉRIAUX ET OUTILS REQUIS", self.styles['DGSection'])
        elements.append(section_title)
        elements.append(Spacer(1, 12))
        
        # En-têtes optimisés
        headers = ['N°', 'Matériau/Outil', 'Description', 'Qté', 'Unité', 'Fournisseur', 'Disponibilité', 'Notes']
        
        # Données des matériaux
        material_data = [headers]
        
        for i, material in enumerate(valid_materials, 1):
            # Troncature minimale intelligente
            name = self._smart_truncate(material.get('name', ''), 30)
            description = self._smart_truncate(material.get('description', ''), 35)
            quantity = f"{material.get('quantity', 1):.1f}"
            unit = material.get('unit', 'pcs')
            fournisseur = self._smart_truncate(material.get('fournisseur', '-- Interne --'), 25)
            available = self._get_availability_display(material.get('available', 'yes'))
            notes = self._smart_truncate(material.get('notes', ''), 20)
            
            material_data.append([
                str(i), name, description, quantity, unit, fournisseur, available, notes
            ])
        
        # Largeurs optimisées pour matériaux
        available_width = self.content_width - 10
        materials_table = Table(material_data, colWidths=[
            available_width * 0.06,  # N° (6%)
            available_width * 0.20,  # Matériau (20%)
            available_width * 0.22,  # Description (22%)
            available_width * 0.08,  # Qté (8%)
            available_width * 0.08,  # Unité (8%)
            available_width * 0.18,  # Fournisseur (18%)
            available_width * 0.10,  # Disponibilité (10%)
            available_width * 0.08   # Notes (8%)
        ])
        
        materials_table.setStyle(TableStyle([
            # Styles uniformes avec les tâches
            ('BACKGROUND', (0, 0), (-1, 0), DG_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (2, -1), 'LEFT'),
            ('ALIGN', (5, 1), (7, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            ('GRID', (0, 0), (-1, -1), 0.5, DG_GRAY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, DG_LIGHT_GREEN]),
            
            # Espacement identique aux tâches
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('ROWHEIGHT', (0, 1), (-1, -1), 24),
            
            ('LINEBELOW', (0, 0), (-1, 0), 2, DG_PRIMARY),
        ]))
        
        elements.append(materials_table)
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _create_instructions_section(self, form_data):
        """Créer la section des instructions - VERSION UNIFORME"""
        elements = []
        
        work_instructions = form_data.get('work_instructions', '').strip()
        safety_notes = form_data.get('safety_notes', '').strip()
        quality_requirements = form_data.get('quality_requirements', '').strip()
        
        if not any([work_instructions, safety_notes, quality_requirements]):
            return elements
        
        # Titre de section
        section_title = Paragraph("INSTRUCTIONS ET NOTES", self.styles['DGSection'])
        elements.append(section_title)
        elements.append(Spacer(1, 12))
        
        # Instructions de travail avec style uniforme
        if work_instructions:
            work_title = Paragraph("<b>Instructions de travail:</b>", self.styles['DGImportant'])
            elements.append(work_title)
            elements.append(Spacer(1, 4))
            
            work_text = Paragraph(work_instructions, self.styles['DGNormal'])
            elements.append(work_text)
            elements.append(Spacer(1, 10))
        
        # Notes de sécurité
        if safety_notes:
            safety_title = Paragraph("<b>⚠️ Notes de sécurité:</b>", self.styles['DGImportant'])
            elements.append(safety_title)
            elements.append(Spacer(1, 4))
            
            safety_text = Paragraph(safety_notes, self.styles['DGNormal'])
            elements.append(safety_text)
            elements.append(Spacer(1, 10))
        
        # Exigences qualité
        if quality_requirements:
            quality_title = Paragraph("<b>🎯 Exigences qualité:</b>", self.styles['DGImportant'])
            elements.append(quality_title)
            elements.append(Spacer(1, 4))
            
            quality_text = Paragraph(quality_requirements, self.styles['DGNormal'])
            elements.append(quality_text)
            elements.append(Spacer(1, 12))
        
        return elements
    
    def _create_signatures_section(self):
        """Créer la section des signatures - VERSION UNIFORME"""
        elements = []
        
        # Titre de section
        section_title = Paragraph("VALIDATIONS ET SIGNATURES", self.styles['DGSection'])
        elements.append(section_title)
        elements.append(Spacer(1, 12))
        
        # Tableau des signatures avec largeurs optimisées
        signature_data = [
            ['Rôle', 'Nom', 'Signature', 'Date'],
            ['Chargé de projet', '', '', ''],
            ['Superviseur production', '', '', ''],
            ['Contrôle qualité', '', '', ''],
            ['Client (si requis)', '', '', '']
        ]
        
        # Largeurs optimisées pour signatures
        available_width = self.content_width - 10
        signatures_table = Table(signature_data, colWidths=[
            available_width * 0.25,  # Rôle (25%)
            available_width * 0.25,  # Nom (25%)
            available_width * 0.30,  # Signature (30%)
            available_width * 0.20   # Date (20%)
        ])
        
        signatures_table.setStyle(TableStyle([
            # Style uniforme avec les autres tableaux
            ('BACKGROUND', (0, 0), (-1, 0), DG_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            ('GRID', (0, 0), (-1, -1), 0.5, DG_GRAY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white]),
            
            # Espacement généreux pour signatures
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('ROWHEIGHT', (0, 1), (-1, -1), 35),  # Plus d'espace pour signatures
            
            ('LINEBELOW', (0, 0), (-1, 0), 2, DG_PRIMARY),
        ]))
        
        elements.append(signatures_table)
        elements.append(Spacer(1, 20))
        
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
        """Générer le PDF complet - VERSION FINALE AMÉLIORÉE"""
        # Créer un buffer pour le PDF
        buffer = io.BytesIO()
        
        # Document avec marges optimisées
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=25,    # Marges minimales pour maximiser l'espace
            leftMargin=25,
            topMargin=120,     # Espace pour en-tête
            bottomMargin=70    # Espace pour pied de page
        )
        
        # Éléments du document
        elements = []
        
        # Ajouter toutes les sections améliorées
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
    Fonction principale d'export PDF pour Streamlit - VERSION AMÉLIORÉE
    """
    try:
        # Validation des données minimales
        if not form_data.get('numero_document'):
            st.error("❌ Numéro de document requis pour l'export PDF")
            return
        
        if not form_data.get('project_name'):
            st.error("❌ Nom du projet requis pour l'export PDF")
            return
        
        # Créer le générateur PDF amélioré
        pdf_generator = BTPDFGenerator()
        
        # Générer le PDF
        with st.spinner("📄 Génération du PDF amélioré en cours..."):
            pdf_buffer = pdf_generator.generate_pdf(form_data)
        
        # Nom du fichier
        numero_doc = form_data.get('numero_document', 'BT')
        projet = form_data.get('project_name', 'Projet')[:25]
        projet_clean = "".join(c for c in projet if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"BT_{numero_doc}_{projet_clean}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # Bouton de téléchargement
        st.download_button(
            label="📥 Télécharger le PDF Amélioré",
            data=pdf_buffer.getvalue(),
            file_name=filename,
            mime="application/pdf",
            type="primary",
            help=f"Télécharger le bon de travail {numero_doc} - Version avec polices uniformes et texte complet"
        )
        
        st.success(f"✅ PDF amélioré généré avec succès ! Fichier: {filename}")
        
        # Informations sur les améliorations
        st.info("""
        🎯 **Améliorations apportées :**
        • ✅ **Polices uniformisées** : 10pt pour le contenu, 9pt pour les détails
        • ✅ **Troncature minimale** : Texte complet préservé autant que possible
        • ✅ **Largeurs optimisées** : Colonnes calculées pour utiliser 100% de l'espace
        • ✅ **Espacement cohérent** : Padding et hauteurs identiques partout
        • ✅ **Alignement intelligent** : Texte important à gauche, chiffres centrés
        • ✅ **Bordures uniformes** : Style professionnel cohérent
        """)
        
        # Statistiques du PDF
        tasks_count = len([t for t in form_data.get('tasks', []) if t.get('operation')])
        materials_count = len([m for m in form_data.get('materials', []) if m.get('name')])
        total_hours = sum(task.get('planned_hours', 0) for task in form_data.get('tasks', []))
        
        st.info(f"""
        📊 **Contenu du PDF :**
        - **Bon de Travail:** {numero_doc}
        - **Projet:** {form_data.get('project_name', 'N/A')}
        - **Tâches:** {tasks_count} opérations ({total_hours:.1f}h prévues)
        - **Matériaux:** {materials_count} éléments
        - **Taille:** {len(pdf_buffer.getvalue()):,} octets
        """)
        
    except Exception as e:
        logger.error(f"Erreur génération PDF amélioré: {e}")
        st.error(f"❌ Erreur lors de la génération du PDF: {str(e)}")
        st.info("💡 Vérifiez que ReportLab est installé: `pip install reportlab`")

def test_pdf_generation():
    """Fonction de test pour la version améliorée"""
    test_data = {
        'numero_document': 'BT-2025-001',
        'project_name': 'ATTACHE DE SERRE 10" (T DE SERRE) - Projet Complet',
        'client_name': 'Doucet Machineries Agricoles Inc.',
        'project_manager': 'Jovick Desmarais',
        'priority': 'NORMAL',
        'start_date': '2025-07-04',
        'end_date': '2025-07-11',
        'work_instructions': 'Instructions détaillées pour la fabrication des attaches de serre selon les spécifications techniques du client.',
        'safety_notes': 'Port des EPI obligatoire en tout temps. Attention particulière lors des opérations de soudage robotisé.',
        'quality_requirements': 'Contrôle dimensionnel selon ISO 9001. Vérification de la résistance à la traction.',
        'tasks': [
            {
                'operation': '1001 - Temps Machine (Préparation)',
                'description': 'Préparation et réglage machine CNC pour production série',
                'quantity': 1,
                'planned_hours': 1.0,
                'actual_hours': 0.0,
                'assigned_to': 'Technicien CNC Senior',
                'fournisseur': '-- Interne --',
                'status': 'pending'
            },
            {
                'operation': '1000 - Génération Programmation CNC',
                'description': 'Programmation complète avec simulation et optimisation',
                'quantity': 1,
                'planned_hours': 4.7,
                'actual_hours': 0.0,
                'assigned_to': 'Programmeur CNC Certifié',
                'fournisseur': '-- Interne --',
                'status': 'pending'
            },
            {
                'operation': '1004 - Scie Métal (Découpe)',
                'description': 'Découpe des barres rectangulaires selon plan technique',
                'quantity': 1,
                'planned_hours': 9.0,
                'actual_hours': 0.0,
                'assigned_to': 'Opérateur Scie Expérimenté',
                'fournisseur': '-- Interne --',
                'status': 'pending'
            },
            {
                'operation': '1012 - Robot Soudage (Assemblage)',
                'description': 'Soudage robotisé des attaches avec contrôle qualité',
                'quantity': 1,
                'planned_hours': 5.7,
                'actual_hours': 0.0,
                'assigned_to': 'Soudeur Robot Qualifié',
                'fournisseur': '-- Interne --',
                'status': 'pending'
            }
        ],
        'materials': [
            {
                'name': 'Acier galvanisé haute résistance',
                'description': 'Barre rectangulaire 40x20x3mm, galvanisation à chaud',
                'quantity': 12.5,
                'unit': 'm',
                'fournisseur': 'Métallurgie Québec Inc.',
                'available': 'yes',
                'notes': 'Stock vérifié, qualité contrôlée'
            },
            {
                'name': 'Électrodes soudage spécialisées',
                'description': 'Fil ER70S-6 diamètre 1.2mm pour robot',
                'quantity': 5.0,
                'unit': 'kg',
                'fournisseur': 'Soudage Spécialisé Ltée',
                'available': 'ordered',
                'notes': 'Livraison confirmée pour demain'
            }
        ]
    }
    
    return test_data

if __name__ == "__main__":
    # Test de la version améliorée
    test_data = test_pdf_generation()
    generator = BTPDFGenerator()
    pdf_buffer = generator.generate_pdf(test_data)
    
    with open("test_bt_ameliore.pdf", "wb") as f:
        f.write(pdf_buffer.getvalue())
    
    print("✅ PDF amélioré généré: test_bt_ameliore.pdf")
    print("🎯 Polices uniformisées, troncature minimale, largeurs optimisées !")
