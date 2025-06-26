# bt_pdf_export.py - Export PDF des Bons de Travail - Desmarais & Gagné Inc.
# Module d'export PDF professionnel pour les Bons de Travail
# Design cohérent avec l'identité visuelle DG Inc.
# VERSION PROFESSIONNELLE AMÉLIORÉE - Design moderne et élégant

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
    Générateur PDF pour les Bons de Travail DG Inc.
    Design professionnel moderne avec mise en page avancée
    """
    
    def __init__(self):
        self.page_width, self.page_height = A4
        self.margin = 2*cm
        self.content_width = self.page_width - 2*self.margin
        
        # Palette de couleurs DG Inc. étendue
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
        """Configure les styles personnalisés DG Inc. améliorés"""
        self.styles = getSampleStyleSheet()
        
        # Style titre principal
        self.styles.add(ParagraphStyle(
            name='DGTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            textColor=self.dg_green_dark,
            spaceAfter=25,
            spaceBefore=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            borderWidth=2,
            borderColor=self.dg_green,
            borderPadding=15,
            backColor=self.dg_green_ultra_light,
            borderRadius=8
        ))
        
        # Style sous-titre élégant
        self.styles.add(ParagraphStyle(
            name='DGSubTitle',
            parent=self.styles['Heading2'],
            fontSize=18,
            textColor=self.dg_green,
            spaceAfter=20,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        ))
        
        # Style section avec design moderne
        self.styles.add(ParagraphStyle(
            name='DGSection',
            parent=self.styles['Heading3'],
            fontSize=16,
            textColor=colors.white,
            spaceAfter=15,
            spaceBefore=25,
            fontName='Helvetica-Bold',
            borderWidth=0,
            borderPadding=12,
            backColor=self.dg_green,
            alignment=TA_LEFT,
            leftIndent=10
        ))
        
        # Style sous-section
        self.styles.add(ParagraphStyle(
            name='DGSubSection',
            parent=self.styles['Heading4'],
            fontSize=14,
            textColor=self.dg_green_dark,
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold',
            borderWidth=1,
            borderColor=self.dg_green_light,
            borderPadding=8,
            backColor=self.dg_green_ultra_light,
            leftIndent=5
        ))
        
        # Style normal amélioré
        self.styles.add(ParagraphStyle(
            name='DGNormal',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=self.dg_gray,
            spaceAfter=8,
            fontName='Helvetica',
            alignment=TA_JUSTIFY
        ))
        
        # Style important avec emphase
        self.styles.add(ParagraphStyle(
            name='DGImportant',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=self.dg_green_dark,
            fontName='Helvetica-Bold',
            spaceAfter=8,
            leftIndent=10,
            borderWidth=1,
            borderColor=self.dg_green,
            borderPadding=8,
            backColor=self.dg_green_ultra_light
        ))
        
        # Style pour les totaux
        self.styles.add(ParagraphStyle(
            name='DGTotal',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=self.dg_green_dark,
            fontName='Helvetica-Bold',
            spaceAfter=10,
            spaceBefore=10,
            alignment=TA_RIGHT,
            borderWidth=2,
            borderColor=self.dg_green,
            borderPadding=10,
            backColor=self.dg_green_light
        ))

    def create_header_footer(self, canvas, doc):
        """Crée l'en-tête et le pied de page DG Inc. améliorés"""
        canvas.saveState()
        
        # === EN-TÊTE MODERNE ===
        # Fond dégradé pour l'en-tête
        header_height = 70
        canvas.setFillColor(self.dg_green_dark)
        canvas.rect(0, self.page_height - header_height, self.page_width, header_height, fill=1)
        
        # Accent décoratif
        canvas.setFillColor(self.dg_green)
        canvas.rect(0, self.page_height - header_height, self.page_width, 5, fill=1)
        
        # Logo DG moderne avec ombre
        logo_x = self.margin
        logo_y = self.page_height - header_height + 15
        
        # Ombre du logo
        canvas.setFillColor(colors.Color(0, 0, 0, 0.3))
        canvas.roundRect(logo_x + 2, logo_y - 2, 70, 40, 8, fill=1)
        
        # Logo principal
        canvas.setFillColor(colors.white)
        canvas.roundRect(logo_x, logo_y, 70, 40, 8, fill=1)
        canvas.setFillColor(self.dg_green_dark)
        canvas.setFont('Helvetica-Bold', 18)
        canvas.drawCentredString(logo_x + 35, logo_y + 18, "DG")
        
        # Nom de l'entreprise avec style
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 22)
        canvas.drawString(logo_x + 90, logo_y + 28, "Desmarais & Gagné inc.")
        
        # Sous-titre élégant
        canvas.setFont('Helvetica', 12)
        canvas.drawString(logo_x + 90, logo_y + 8, "Solutions industrielles d'excellence")
        
        # Coordonnées dans un encadré moderne
        contact_x = self.page_width - self.margin - 200
        contact_y = logo_y
        
        # Fond des coordonnées
        canvas.setFillColor(colors.Color(1, 1, 1, 0.15))
        canvas.roundRect(contact_x - 10, contact_y - 5, 210, 45, 5, fill=1)
        
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica', 10)
        canvas.drawRightString(self.page_width - self.margin, contact_y + 30, "565 rue Maisonneuve, Granby, QC J2G 3H5")
        canvas.drawRightString(self.page_width - self.margin, contact_y + 18, "Tél.: (450) 372-9630")
        canvas.drawRightString(self.page_width - self.margin, contact_y + 6, "Téléc.: (450) 372-8122")
        
        # === PIED DE PAGE ÉLÉGANT ===
        footer_height = 40
        footer_y = self.margin - 15
        
        # Ligne décorative
        canvas.setStrokeColor(self.dg_green)
        canvas.setLineWidth(2)
        canvas.line(self.margin, footer_y + 25, self.page_width - self.margin, footer_y + 25)
        
        # Fond du pied de page
        canvas.setFillColor(self.dg_gray_ultra_light)
        canvas.rect(self.margin, footer_y - 10, self.content_width, 30, fill=1)
        
        # Informations du pied de page
        canvas.setFillColor(self.dg_gray)
        canvas.setFont('Helvetica', 9)
        
        # Date de génération
        date_text = f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
        canvas.drawString(self.margin + 10, footer_y + 5, date_text)
        
        # Titre centré
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(self.page_width/2, footer_y + 5, "BON DE TRAVAIL - Système ERP DG Inc.")
        
        # Numéro de page avec style
        page_text = f"Page {doc.page}"
        canvas.setFont('Helvetica', 9)
        canvas.drawRightString(self.page_width - self.margin - 10, footer_y + 5, page_text)
        
        canvas.restoreState()

    def export_bt_to_pdf(self, form_data):
        """
        Génère le PDF du Bon de Travail avec design professionnel
        
        Args:
            form_data (dict): Données du formulaire BT
            
        Returns:
            bytes: Contenu du PDF généré
        """
        try:
            # Créer un buffer en mémoire
            buffer = io.BytesIO()
            
            # Créer le document PDF avec marges optimisées
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=self.margin,
                leftMargin=self.margin,
                topMargin=self.margin + 80,  # Espace pour l'en-tête amélioré
                bottomMargin=self.margin + 50  # Espace pour le pied de page amélioré
            )
            
            # Construire le contenu
            story = []
            
            # Titre principal avec design moderne
            story.append(Paragraph("🔧 BON DE TRAVAIL", self.styles['DGTitle']))
            story.append(Spacer(1, 20))
            
            # Badge de statut
            self._add_status_badge(story, form_data)
            story.append(Spacer(1, 15))
            
            # Informations générales avec design amélioré
            self._add_general_info(story, form_data)
            story.append(Spacer(1, 20))
            
            # Tâches et opérations avec tableaux stylés
            self._add_tasks_section(story, form_data)
            story.append(Spacer(1, 20))
            
            # Matériaux avec design moderne
            self._add_materials_section(story, form_data)
            story.append(Spacer(1, 20))
            
            # Instructions avec sections bien délimitées
            self._add_instructions_section(story, form_data)
            story.append(Spacer(1, 20))
            
            # Signatures avec design professionnel
            self._add_signatures_section(story)
            
            # Construire le PDF avec en-tête/pied de page améliorés
            doc.build(story, onFirstPage=self.create_header_footer, 
                     onLaterPages=self.create_header_footer)
            
            # Récupérer le contenu
            pdf_content = buffer.getvalue()
            buffer.close()
            
            logger.info(f"PDF professionnel généré avec succès pour BT {form_data.get('numero_document', 'N/A')}")
            return pdf_content
            
        except Exception as e:
            logger.error(f"Erreur génération PDF professionnel: {e}")
            raise e

    def _add_status_badge(self, story, form_data):
        """Ajoute un badge de statut et priorité moderne"""
        priority = form_data.get('priority', 'NORMAL')
        statut = form_data.get('statut', 'BROUILLON')
        
        # Couleurs selon la priorité
        priority_colors = {
            'CRITIQUE': self.dg_red,
            'URGENT': self.dg_orange,
            'NORMAL': self.dg_green
        }
        
        priority_color = priority_colors.get(priority, self.dg_green)
        
        badge_data = [
            ['Numéro:', form_data.get('numero_document', 'N/A'), 'Priorité:', self._format_priority(priority), 'Statut:', statut]
        ]
        
        badge_table = Table(badge_data, colWidths=[2*cm, 4*cm, 2*cm, 3*cm, 2*cm, 3*cm])
        badge_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.dg_green_ultra_light),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.dg_gray),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 2, self.dg_green),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [self.dg_green_light]),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        story.append(badge_table)

    def _add_general_info(self, story, form_data):
        """Ajoute les informations générales avec design moderne"""
        story.append(Paragraph("📋 INFORMATIONS GÉNÉRALES", self.styles['DGSection']))
        story.append(Spacer(1, 10))
        
        # Tableau principal des informations
        data = [
            ['🏗️ Projet:', form_data.get('project_name', 'N/A')],
            ['🏢 Client:', form_data.get('client_name', 'N/A')],
            ['👤 Chargé de projet:', form_data.get('project_manager', 'Non assigné')],
            ['📅 Date début:', form_data.get('start_date', 'N/A')],
            ['📅 Date fin prévue:', form_data.get('end_date', 'N/A')],
        ]
        
        table = Table(data, colWidths=[4.5*cm, 11*cm])
        table.setStyle(TableStyle([
            # En-têtes avec style moderne
            ('BACKGROUND', (0, 0), (0, -1), self.dg_green),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, self.dg_green_light),
            ('ROWBACKGROUNDS', (1, 0), (1, -1), [colors.white, self.dg_gray_ultra_light]),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ]))
        
        story.append(table)

    def _add_tasks_section(self, story, form_data):
        """Ajoute la section des tâches avec design professionnel"""
        story.append(Paragraph("⚙️ TÂCHES ET OPÉRATIONS", self.styles['DGSection']))
        story.append(Spacer(1, 10))
        
        tasks = form_data.get('tasks', [])
        
        if not tasks or not any(t.get('operation') or t.get('description') for t in tasks):
            no_task_text = "Aucune tâche définie pour ce bon de travail."
            story.append(Paragraph(no_task_text, self.styles['DGNormal']))
            return
        
        # En-têtes du tableau avec icônes
        headers = ['🔧 Opération', '📝 Description', 'Qté', '⏱️ H.Prév', '✅ H.Réel', '👤 Assigné', '🏢 Fournisseur', '📊 Statut']
        data = [headers]
        
        total_planned = 0
        total_actual = 0
        internal_planned = 0
        external_planned = 0
        
        # Couleurs alternées pour les lignes
        row_colors = [colors.white, self.dg_gray_ultra_light]
        
        for i, task in enumerate(tasks, 1):
            if task.get('operation') or task.get('description'):
                operation = task.get('operation', '')
                description = task.get('description', '')
                quantity = task.get('quantity', 1)
                planned_hours = task.get('planned_hours', 0.0)
                actual_hours = task.get('actual_hours', 0.0)
                assigned_to = task.get('assigned_to', '')
                fournisseur = task.get('fournisseur', '-- Interne --')
                status = self._format_status(task.get('status', 'pending'))
                
                # Calculer les totaux
                total_planned += planned_hours
                total_actual += actual_hours
                
                if fournisseur == '-- Interne --':
                    internal_planned += planned_hours
                else:
                    external_planned += planned_hours
                
                # Tronquer les textes longs avec élégance
                operation_display = operation[:18] + '...' if len(operation) > 18 else operation
                description_display = description[:25] + '...' if len(description) > 25 else description
                assigned_display = assigned_to[:15] + '...' if len(assigned_to) > 15 else assigned_to
                fournisseur_display = fournisseur[:18] + '...' if len(fournisseur) > 18 else fournisseur
                
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
        
        # Ligne de totaux avec style spécial
        data.append([
            'TOTAUX', '', '', 
            f"{total_planned:.1f}h", 
            f"{total_actual:.1f}h", 
            '', '', ''
        ])
        
        # Créer le tableau avec style professionnel
        table = Table(data, colWidths=[2.2*cm, 2.8*cm, 1*cm, 1.3*cm, 1.3*cm, 2*cm, 2.2*cm, 1.5*cm])
        table.setStyle(TableStyle([
            # En-têtes avec dégradé
            ('BACKGROUND', (0, 0), (-1, 0), self.dg_green_dark),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Données avec alternance de couleurs
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('ALIGN', (2, 1), (4, -1), 'CENTER'),  # Colonnes numériques
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Ligne totaux avec mise en évidence
            ('BACKGROUND', (0, -1), (-1, -1), self.dg_green),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            
            # Grille moderne
            ('GRID', (0, 0), (-1, -1), 0.5, self.dg_green_light),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), row_colors),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(table)
        
        # Répartition interne/externe avec style
        if external_planned > 0:
            story.append(Spacer(1, 15))
            repartition_text = f"📊 <b>Répartition des heures:</b> Interne: {internal_planned:.1f}h • Externe: {external_planned:.1f}h • Total: {total_planned:.1f}h"
            story.append(Paragraph(repartition_text, self.styles['DGImportant']))

    def _add_materials_section(self, story, form_data):
        """Ajoute la section des matériaux avec design moderne"""
        story.append(Paragraph("📦 MATÉRIAUX ET OUTILS REQUIS", self.styles['DGSection']))
        story.append(Spacer(1, 10))
        
        materials = form_data.get('materials', [])
        
        if not materials or not any(m.get('name') for m in materials):
            no_material_text = "Aucun matériau ou outil spécifié pour ce bon de travail."
            story.append(Paragraph(no_material_text, self.styles['DGNormal']))
            return
        
        # En-têtes avec icônes
        headers = ['📦 Matériau/Outil', '📝 Description', 'Qté', '📏 Unité', '🏢 Fournisseur', '✅ Disponibilité', '📋 Notes']
        data = [headers]
        
        for material in materials:
            if material.get('name'):
                name = material.get('name', '')
                description = material.get('description', '')
                quantity = material.get('quantity', 1.0)
                unit = material.get('unit', 'pcs')
                fournisseur = material.get('fournisseur', '-- Interne --')
                available = self._format_availability(material.get('available', 'yes'))
                notes = material.get('notes', '')
                
                # Tronquer les textes avec élégance
                name_display = name[:22] + '...' if len(name) > 22 else name
                description_display = description[:28] + '...' if len(description) > 28 else description
                fournisseur_display = fournisseur[:18] + '...' if len(fournisseur) > 18 else fournisseur
                notes_display = notes[:25] + '...' if len(notes) > 25 else notes
                
                data.append([
                    name_display,
                    description_display,
                    f"{quantity:.1f}",
                    unit,
                    fournisseur_display,
                    available,
                    notes_display
                ])
        
        # Créer le tableau avec style moderne
        table = Table(data, colWidths=[3.2*cm, 3.5*cm, 1.2*cm, 1*cm, 2.8*cm, 2.2*cm, 2.5*cm])
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
            ('ALIGN', (2, 1), (3, -1), 'CENTER'),  # Quantité et unité
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Style moderne
            ('GRID', (0, 0), (-1, -1), 0.5, self.dg_gray_light),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.dg_gray_ultra_light]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(table)

    def _add_instructions_section(self, story, form_data):
        """Ajoute la section des instructions avec design structuré"""
        story.append(Paragraph("📋 INSTRUCTIONS ET NOTES", self.styles['DGSection']))
        story.append(Spacer(1, 10))
        
        # Instructions de travail
        work_instructions = form_data.get('work_instructions', '')
        if work_instructions:
            story.append(Paragraph("🔧 Instructions de travail", self.styles['DGSubSection']))
            story.append(Paragraph(work_instructions, self.styles['DGNormal']))
            story.append(Spacer(1, 12))
        
        # Notes de sécurité avec mise en évidence
        safety_notes = form_data.get('safety_notes', '')
        if safety_notes:
            story.append(Paragraph("🛡️ Notes de sécurité", self.styles['DGSubSection']))
            story.append(Paragraph(safety_notes, self.styles['DGImportant']))
            story.append(Spacer(1, 12))
        
        # Exigences qualité
        quality_requirements = form_data.get('quality_requirements', '')
        if quality_requirements:
            story.append(Paragraph("🎯 Exigences qualité", self.styles['DGSubSection']))
            story.append(Paragraph(quality_requirements, self.styles['DGNormal']))

    def _add_signatures_section(self, story):
        """Ajoute la section des signatures avec design professionnel"""
        story.append(Spacer(1, 30))
        story.append(Paragraph("✍️ SIGNATURES ET APPROBATIONS", self.styles['DGSection']))
        story.append(Spacer(1, 15))
        
        # Tableau des signatures moderne
        sig_data = [
            ['👤 Préparé par:', '', '📅 Date:', '', '👤 Approuvé par:', '', '📅 Date:', ''],
            ['', '', '', '', '', '', '', ''],
            ['✍️ Signature:', '', '', '', '✍️ Signature:', '', '', ''],
            ['', '', '', '', '', '', '', ''],
        ]
        
        sig_table = Table(sig_data, colWidths=[2.5*cm, 3.5*cm, 1.5*cm, 2*cm, 2.5*cm, 3.5*cm, 1.5*cm, 2*cm])
        sig_table.setStyle(TableStyle([
            # Style moderne pour les signatures
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, 0), self.dg_green_light),
            ('BACKGROUND', (0, 2), (-1, 2), self.dg_green_light),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.dg_gray),
            ('GRID', (0, 0), (-1, -1), 1, self.dg_green_light),
            
            # Lignes pour les signatures
            ('LINEBELOW', (1, 2), (1, 2), 1, self.dg_gray),  # Signature 1
            ('LINEBELOW', (3, 2), (3, 2), 1, self.dg_gray),  # Date 1
            ('LINEBELOW', (5, 2), (5, 2), 1, self.dg_gray),  # Signature 2
            ('LINEBELOW', (7, 2), (7, 2), 1, self.dg_gray),  # Date 2
            
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(sig_table)
        
        # Note légale
        story.append(Spacer(1, 20))
        legal_note = "Ce document constitue un engagement contractuel. Toute modification doit être approuvée par écrit."
        story.append(Paragraph(legal_note, self.styles['DGNormal']))

    def _format_priority(self, priority):
        """Formate la priorité avec des icônes modernes"""
        priority_map = {
            'NORMAL': '🟢 Normal',
            'URGENT': '🟡 Urgent',
            'CRITIQUE': '🔴 Critique'
        }
        return priority_map.get(priority, priority)

    def _format_status(self, status):
        """Formate le statut des tâches avec des icônes"""
        status_map = {
            'pending': '⏳ En attente',
            'in-progress': '🔄 En cours',
            'completed': '✅ Terminé',
            'on-hold': '⏸️ En pause'
        }
        return status_map.get(status, status)

    def _format_availability(self, availability):
        """Formate la disponibilité des matériaux avec des icônes"""
        avail_map = {
            'yes': '✅ Disponible',
            'no': '❌ Non dispo',
            'partial': '⚠️ Partiel',
            'ordered': '📦 Commandé'
        }
        return avail_map.get(availability, availability)


def export_bt_pdf_streamlit(form_data):
    """
    Interface Streamlit pour l'export PDF professionnel
    
    Args:
        form_data (dict): Données du Bon de Travail
    """
    try:
        # Créer l'exporteur
        exporter = BTToPDFExporter()
        
        # Générer le PDF
        with st.spinner("🎨 Génération du PDF professionnel en cours..."):
            pdf_content = exporter.export_bt_to_pdf(form_data)
        
        # Nom du fichier
        numero_document = form_data.get('numero_document', 'BT')
        filename = f"BT_Pro_{numero_document}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Bouton de téléchargement avec style
        st.download_button(
            label="📄 Télécharger le PDF Professionnel",
            data=pdf_content,
            file_name=filename,
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        
        st.success(f"✨ PDF professionnel généré avec succès ! **{filename}**")
        
        # Statistiques détaillées
        tasks_count = len([t for t in form_data.get('tasks', []) if t.get('operation') or t.get('description')])
        materials_count = len([m for m in form_data.get('materials', []) if m.get('name')])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Tâches", tasks_count)
        with col2:
            st.metric("📦 Matériaux", materials_count)
        with col3:
            st.metric("📄 Taille", f"{len(pdf_content):,} bytes")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la génération du PDF professionnel: {e}")
        logger.error(f"Erreur export PDF professionnel: {e}")
        return False


# Test unitaire avec design professionnel
if __name__ == "__main__":
    # Données d'exemple complètes pour test
    sample_data = {
        'numero_document': 'BT-PRO-2025-001',
        'project_name': 'Modernisation Ligne de Production #3',
        'client_name': 'Industries Avancées Québec Inc.',
        'project_manager': 'Jean-Pierre Martin',
        'priority': 'URGENT',
        'start_date': '2025-01-15',
        'end_date': '2025-02-28',
        'statut': 'VALIDÉ',
        'work_instructions': '''Procéder à la modernisation complète de la ligne de production #3 selon les spécifications techniques détaillées dans le cahier des charges v2.1.

Étapes principales du projet :
1. Audit complet de l'installation existante
2. Démontage sécurisé des équipements obsolètes
3. Préparation et mise à niveau des infrastructures
4. Installation des nouveaux systèmes robotisés
5. Tests de fonctionnement et optimisation
6. Formation du personnel et mise en service

Respect strict des normes ISO 9001:2015 et des procédures DG Inc.''',
        'safety_notes': '''⚠️ CONSIGNES DE SÉCURITÉ STRICTES ⚠️

• Port obligatoire des EPI complets en permanence
• Zone de travail sécurisée avec périmètre de sécurité
• Procédure LOTO (Lock-Out Tag-Out) pour tous les équipements
• Présence obligatoire d'un responsable sécurité
• Vérification quotidienne des équipements de levage
• Formation sécurité obligatoire pour tout intervenant

En cas d'urgence, contacter immédiatement le responsable sécurité au poste 911.''',
        'quality_requirements': '''Standards qualité selon ISO 9001:2015 et normes DG Inc.

Points de contrôle obligatoires :
• Vérification dimensionnelle à chaque étape
• Tests de fonctionnement selon protocoles
• Validation par responsable qualité
• Documentation complète des interventions
• Traçabilité des matériaux et composants
• Contrôle final par organisme externe

Critères d'acceptation : 99.5% de conformité minimale.''',
        'tasks': [
            {
                'operation': 'Découpe plasma CNC',
                'description': 'Découpe précision des plaques selon plans CAO',
                'quantity': 24,
                'planned_hours': 12.0,
                'actual_hours': 11.5,
                'assigned_to': 'Pierre Gagnon',
                'fournisseur': '-- Interne --',
                'status': 'completed'
            },
            {
                'operation': 'Soudage robotisé TIG',
                'description': 'Assemblage structures principales robot ABB',
                'quantity': 12,
                'planned_hours': 20.0,
                'actual_hours': 18.5,
                'assigned_to': 'Marie Dubois',
                'fournisseur': '-- Interne --',
                'status': 'completed'
            },
            {
                'operation': 'Traitement thermique',
                'description': 'Normalisation contraintes et durcissement',
                'quantity': 12,
                'planned_hours': 8.0,
                'actual_hours': 0.0,
                'assigned_to': 'Jean Lafleur (Resp. Tech)',
                'fournisseur': 'Traitement Thermique Granby Inc.',
                'status': 'in-progress'
            },
            {
                'operation': 'Usinage CNC 5 axes',
                'description': 'Finition précision ±0.05mm des fixations',
                'quantity': 48,
                'planned_hours': 16.0,
                'actual_hours': 14.0,
                'assigned_to': 'Louise Tremblay',
                'fournisseur': '-- Interne --',
                'status': 'completed'
            },
            {
                'operation': 'Inspection dimensionnelle',
                'description': 'Contrôle qualité CMM et validation finale',
                'quantity': 1,
                'planned_hours': 4.0,
                'actual_hours': 0.0,
                'assigned_to': 'Inspecteur Certifié',
                'fournisseur': 'Bureau Veritas Québec',
                'status': 'pending'
            }
        ],
        'materials': [
            {
                'name': 'Plaque acier inoxydable 316L',
                'description': 'Plaque 15mm x 3000mm x 1500mm certifiée',
                'quantity': 8.0,
                'unit': 'pcs',
                'fournisseur': 'Métallurgie Québec Inc.',
                'available': 'yes',
                'notes': 'Certificat matière EN 10204 fourni'
            },
            {
                'name': 'Électrodes TIG ER316L Ø2.4',
                'description': 'Baguettes soudage haute pureté',
                'quantity': 5.0,
                'unit': 'kg',
                'fournisseur': '-- Interne --',
                'available': 'yes',
                'notes': 'Stock atelier - Lot #2025-A'
            },
            {
                'name': 'Boulonnerie inox A4-80',
                'description': 'Vis CHC M12x50 + écrous autobloquants',
                'quantity': 96.0,
                'unit': 'pcs',
                'fournisseur': 'Boulonnerie Industrielle QC',
                'available': 'ordered',
                'notes': 'Livraison confirmée 48h'
            },
            {
                'name': 'Gaz argon 99.998%',
                'description': 'Bouteilles 50L pour soudage TIG',
                'quantity': 3.0,
                'unit': 'pcs',
                'fournisseur': '-- Interne --',
                'available': 'partial',
                'notes': '2 bouteilles dispo, 1 en commande'
            },
            {
                'name': 'Fluide de coupe synthétique',
                'description': 'Lubrifiant usinage haute performance',
                'quantity': 20.0,
                'unit': 'l',
                'fournisseur': 'Chimie Industrielle DG',
                'available': 'yes',
                'notes': 'Bidon 20L neuf'
            }
        ]
    }
    
    # Générer le PDF professionnel de test
    try:
        exporter = BTToPDFExporter()
        pdf_content = exporter.export_bt_to_pdf(sample_data)
        
        # Sauvegarder en fichier de test
        with open('test_bt_professionnel_dg_inc.pdf', 'wb') as f:
            f.write(pdf_content)
        
        print("✨ PDF professionnel de test généré: test_bt_professionnel_dg_inc.pdf")
        print(f"📊 Taille du fichier: {len(pdf_content):,} bytes")
        print("🎨 Design moderne avec couleurs DG Inc., icônes et mise en page professionnelle")
        
    except Exception as e:
        print(f"❌ Erreur génération PDF test professionnel: {e}")