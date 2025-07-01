# bt_pdf_export.py - Module d'export PDF pour les Bons de Travail - VERSION CORRIGÉE
# Desmarais & Gagné Inc. - Système ERP Production
# Génération de PDFs professionnels avec identité DG Inc.
# CORRECTION : Utilisation des bonnes méthodes ReportLab

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
    """Générateur de PDF pour les Bons de Travail - VERSION CORRIGÉE"""
    
    def __init__(self):
        self.page_width = A4[0]
        self.page_height = A4[1]
        self.margin = 50
        self.content_width = self.page_width - 2 * self.margin
        
        # Styles
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Créer les styles personnalisés DG Inc."""
        
        # Style titre principal
        self.styles.add(ParagraphStyle(
            name='DGTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=DG_PRIMARY_DARK,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Style sous-titre
        self.styles.add(ParagraphStyle(
            name='DGSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=DG_PRIMARY,
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))
        
        # Style section
        self.styles.add(ParagraphStyle(
            name='DGSection',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=DG_PRIMARY_DARK,
            spaceAfter=8,
            spaceBefore=16,
            fontName='Helvetica-Bold'
        ))
        
        # Style normal DG
        self.styles.add(ParagraphStyle(
            name='DGNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=DG_GRAY,
            spaceAfter=6,
            fontName='Helvetica'
        ))
        
        # Style info importante
        self.styles.add(ParagraphStyle(
            name='DGImportant',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=DG_PRIMARY_DARK,
            fontName='Helvetica-Bold',
            spaceAfter=6
        ))
        
        # Style petite info
        self.styles.add(ParagraphStyle(
            name='DGSmall',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=DG_LIGHT_GRAY,
            fontName='Helvetica'
        ))
    
    def _create_header_footer(self, canvas, doc):
        """Créer l'en-tête et le pied de page - VERSION CORRIGÉE"""
        canvas.saveState()
        
        # En-tête
        # Logo DG simulé (rectangle avec texte)
        canvas.setFillColor(DG_PRIMARY)
        canvas.rect(self.margin, self.page_height - 80, 60, 30, fill=1, stroke=0)
        
        # CORRECTION : Utiliser drawString avec calcul manuel pour centrer
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 16)
        text_width = canvas.stringWidth("DG", 'Helvetica-Bold', 16)
        canvas.drawString(self.margin + 30 - text_width/2, self.page_height - 68, "DG")
        
        # Nom de l'entreprise
        canvas.setFillColor(DG_PRIMARY_DARK)
        canvas.setFont('Helvetica-Bold', 18)
        canvas.drawString(self.margin + 80, self.page_height - 60, "Desmarais & Gagné inc.")
        
        # Coordonnées - CORRECTION : Utiliser drawRightString correctement
        canvas.setFillColor(DG_GRAY)
        canvas.setFont('Helvetica', 9)
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
        
        # Pied de page
        canvas.setFillColor(DG_LIGHT_GRAY)
        canvas.setFont('Helvetica', 8)
        
        # Date d'impression
        date_impression = f"Imprimé le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
        canvas.drawString(self.margin, 30, date_impression)
        
        # Numéro de page
        page_num = f"Page {doc.page}"
        canvas.drawRightString(self.page_width - self.margin, 30, page_num)
        
        # Ligne de pied
        canvas.setStrokeColor(DG_PRIMARY)
        canvas.setLineWidth(1)
        canvas.line(self.margin, 45, self.page_width - self.margin, 45)
        
        canvas.restoreState()
    
    def _create_info_section(self, form_data):
        """Créer la section d'informations générales"""
        elements = []
        
        # Titre du document
        title = Paragraph("BON DE TRAVAIL", self.styles['DGTitle'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Informations principales dans un tableau
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
        
        info_table = Table(info_data, colWidths=[80, 120, 80, 120])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), DG_LIGHT_GREEN),
            ('BACKGROUND', (2, 0), (2, -1), DG_LIGHT_GREEN),
            ('TEXTCOLOR', (0, 0), (-1, -1), DG_GRAY),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, DG_PRIMARY),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, DG_LIGHT_GREEN])
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_tasks_section(self, form_data):
        """Créer la section des tâches"""
        elements = []
        
        tasks = form_data.get('tasks', [])
        if not tasks or not any(task.get('operation') or task.get('description') for task in tasks):
            return elements
        
        # Titre de section
        section_title = Paragraph("TÂCHES ET OPÉRATIONS", self.styles['DGSection'])
        elements.append(section_title)
        
        # En-têtes du tableau
        headers = ['#', 'Opération', 'Description', 'Qté', 'H. Prév.', 'H. Réel.', 'Assigné à', 'Fournisseur', 'Statut']
        
        # Données des tâches
        task_data = [headers]
        
        valid_tasks = [task for task in tasks if task.get('operation') or task.get('description')]
        
        for i, task in enumerate(valid_tasks, 1):
            operation = task.get('operation', '')
            description = task.get('description', '')
            quantity = str(task.get('quantity', 1))
            planned_hours = f"{task.get('planned_hours', 0):.1f}h"
            actual_hours = f"{task.get('actual_hours', 0):.1f}h"
            assigned_to = task.get('assigned_to', '')
            fournisseur = task.get('fournisseur', '-- Interne --')
            status = self._get_status_display(task.get('status', 'pending'))
            
            # Limiter la longueur des textes pour l'affichage
            if len(operation) > 15:
                operation = operation[:12] + "..."
            if len(description) > 20:
                description = description[:17] + "..."
            if len(assigned_to) > 12:
                assigned_to = assigned_to[:9] + "..."
            if len(fournisseur) > 15:
                fournisseur = fournisseur[:12] + "..."
            
            task_data.append([
                str(i), operation, description, quantity, 
                planned_hours, actual_hours, assigned_to, fournisseur, status
            ])
        
        # Créer le tableau
        if len(task_data) > 1:  # Si on a au moins une tâche + headers
            tasks_table = Table(task_data, colWidths=[20, 60, 80, 25, 35, 35, 60, 60, 45])
            tasks_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), DG_PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 1), (2, -1), 'LEFT'),  # Opération et description à gauche
                ('ALIGN', (6, 1), (7, -1), 'LEFT'),  # Assigné et fournisseur à gauche
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, DG_GRAY),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, DG_LIGHT_GREEN])
            ]))
            
            elements.append(tasks_table)
            elements.append(Spacer(1, 10))
            
            # Totaux
            total_planned = sum(task.get('planned_hours', 0) for task in valid_tasks)
            total_actual = sum(task.get('actual_hours', 0) for task in valid_tasks)
            internal_planned = sum(task.get('planned_hours', 0) for task in valid_tasks 
                                 if task.get('fournisseur') == '-- Interne --')
            external_planned = total_planned - internal_planned
            
            totals_text = f"""
            <b>TOTAUX:</b><br/>
            • Heures prévues: <b>{total_planned:.1f}h</b> (Interne: {internal_planned:.1f}h, Externe: {external_planned:.1f}h)<br/>
            • Heures réelles: <b>{total_actual:.1f}h</b><br/>
            • Nombre de tâches: <b>{len(valid_tasks)}</b>
            """
            
            totals_para = Paragraph(totals_text, self.styles['DGImportant'])
            elements.append(totals_para)
            elements.append(Spacer(1, 15))
        
        return elements
    
    def _create_materials_section(self, form_data):
        """Créer la section des matériaux"""
        elements = []
        
        materials = form_data.get('materials', [])
        valid_materials = [mat for mat in materials if mat.get('name')]
        
        if not valid_materials:
            return elements
        
        # Titre de section
        section_title = Paragraph("MATÉRIAUX ET OUTILS REQUIS", self.styles['DGSection'])
        elements.append(section_title)
        
        # En-têtes du tableau
        headers = ['#', 'Matériau/Outil', 'Description', 'Quantité', 'Unité', 'Fournisseur', 'Disponibilité', 'Notes']
        
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
            
            # Limiter la longueur des textes
            if len(name) > 20:
                name = name[:17] + "..."
            if len(description) > 25:
                description = description[:22] + "..."
            if len(fournisseur) > 15:
                fournisseur = fournisseur[:12] + "..."
            if len(notes) > 20:
                notes = notes[:17] + "..."
            
            material_data.append([
                str(i), name, description, quantity, unit, fournisseur, available, notes
            ])
        
        # Créer le tableau
        materials_table = Table(material_data, colWidths=[20, 70, 80, 35, 30, 60, 50, 75])
        materials_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DG_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (2, -1), 'LEFT'),  # Nom et description à gauche
            ('ALIGN', (5, 1), (7, -1), 'LEFT'),  # Fournisseur et notes à gauche
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, DG_GRAY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, DG_LIGHT_GREEN])
        ]))
        
        elements.append(materials_table)
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _create_instructions_section(self, form_data):
        """Créer la section des instructions"""
        elements = []
        
        work_instructions = form_data.get('work_instructions', '').strip()
        safety_notes = form_data.get('safety_notes', '').strip()
        quality_requirements = form_data.get('quality_requirements', '').strip()
        
        if not any([work_instructions, safety_notes, quality_requirements]):
            return elements
        
        # Titre de section
        section_title = Paragraph("INSTRUCTIONS ET NOTES", self.styles['DGSection'])
        elements.append(section_title)
        
        # Instructions de travail
        if work_instructions:
            work_title = Paragraph("<b>Instructions de travail:</b>", self.styles['DGImportant'])
            elements.append(work_title)
            
            work_text = Paragraph(work_instructions, self.styles['DGNormal'])
            elements.append(work_text)
            elements.append(Spacer(1, 10))
        
        # Notes de sécurité
        if safety_notes:
            safety_title = Paragraph("<b>⚠️ Notes de sécurité:</b>", self.styles['DGImportant'])
            elements.append(safety_title)
            
            safety_text = Paragraph(safety_notes, self.styles['DGNormal'])
            elements.append(safety_text)
            elements.append(Spacer(1, 10))
        
        # Exigences qualité
        if quality_requirements:
            quality_title = Paragraph("<b>🎯 Exigences qualité:</b>", self.styles['DGImportant'])
            elements.append(quality_title)
            
            quality_text = Paragraph(quality_requirements, self.styles['DGNormal'])
            elements.append(quality_text)
            elements.append(Spacer(1, 10))
        
        return elements
    
    def _create_signatures_section(self):
        """Créer la section des signatures"""
        elements = []
        
        # Titre de section
        section_title = Paragraph("VALIDATIONS ET SIGNATURES", self.styles['DGSection'])
        elements.append(section_title)
        
        # Tableau des signatures
        signature_data = [
            ['Rôle', 'Nom', 'Signature', 'Date'],
            ['Chargé de projet', '', '', ''],
            ['Superviseur production', '', '', ''],
            ['Contrôle qualité', '', '', ''],
            ['Client (si requis)', '', '', '']
        ]
        
        signatures_table = Table(signature_data, colWidths=[100, 120, 120, 80])
        signatures_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DG_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (1, -1), 'LEFT'),  # Rôle et nom à gauche
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, DG_GRAY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white]),
            ('ROWHEIGHT', (0, 1), (-1, -1), 35)  # Hauteur pour les signatures
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
        """Générer le PDF complet"""
        # Créer un buffer pour le PDF
        buffer = io.BytesIO()
        
        # Créer le document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=120,  # Plus d'espace pour l'en-tête
            bottomMargin=70  # Plus d'espace pour le pied de page
        )
        
        # Éléments du document
        elements = []
        
        # Ajouter toutes les sections
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
    Fonction principale d'export PDF pour Streamlit - VERSION CORRIGÉE
    """
    try:
        # Validation des données minimales
        if not form_data.get('numero_document'):
            st.error("❌ Numéro de document requis pour l'export PDF")
            return
        
        if not form_data.get('project_name'):
            st.error("❌ Nom du projet requis pour l'export PDF")
            return
        
        # Créer le générateur PDF
        pdf_generator = BTPDFGenerator()
        
        # Générer le PDF
        with st.spinner("📄 Génération du PDF en cours..."):
            pdf_buffer = pdf_generator.generate_pdf(form_data)
        
        # Nom du fichier
        numero_doc = form_data.get('numero_document', 'BT')
        projet = form_data.get('project_name', 'Projet')[:20]  # Limiter la longueur
        # Nettoyer le nom pour le fichier
        projet_clean = "".join(c for c in projet if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"BT_{numero_doc}_{projet_clean}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # Bouton de téléchargement
        st.download_button(
            label="📥 Télécharger le PDF",
            data=pdf_buffer.getvalue(),
            file_name=filename,
            mime="application/pdf",
            type="primary",
            help=f"Télécharger le bon de travail {numero_doc} en PDF"
        )
        
        st.success(f"✅ PDF généré avec succès ! Fichier: {filename}")
        
        # Informations sur le PDF généré
        pdf_size = len(pdf_buffer.getvalue())
        st.info(f"""
        📋 **Informations PDF:**
        - **Bon de Travail:** {numero_doc}
        - **Projet:** {form_data.get('project_name', 'N/A')}
        - **Client:** {form_data.get('client_name', 'N/A')}
        - **Taille:** {pdf_size:,} octets
        - **Pages:** Estimation 1-2 pages selon le contenu
        """)
        
    except Exception as e:
        logger.error(f"Erreur génération PDF: {e}")
        st.error(f"❌ Erreur lors de la génération du PDF: {str(e)}")
        st.info("💡 Vérifiez que ReportLab est installé: `pip install reportlab`")

def test_pdf_generation():
    """Fonction de test pour vérifier la génération PDF"""
    test_data = {
        'numero_document': 'BT-2024-001',
        'project_name': 'Projet Test PDF',
        'client_name': 'Client Test',
        'project_manager': 'Jean Dupont',
        'priority': 'NORMAL',
        'start_date': '2024-01-15',
        'end_date': '2024-01-22',
        'work_instructions': 'Instructions de test pour vérifier la génération PDF.',
        'safety_notes': 'Port des EPI obligatoire.',
        'quality_requirements': 'Contrôle dimensionnel selon ISO 9001.',
        'tasks': [
            {
                'operation': 'Programmation CNC',
                'description': 'Programmation pièce complexe',
                'quantity': 1,
                'planned_hours': 4.0,
                'actual_hours': 0.0,
                'assigned_to': 'Programmeur 1',
                'fournisseur': '-- Interne --',
                'status': 'pending'
            }
        ],
        'materials': [
            {
                'name': 'Acier 316L',
                'description': 'Plaque 10mm',
                'quantity': 2.5,
                'unit': 'kg',
                'fournisseur': 'Métallurgie Québec',
                'available': 'yes',
                'notes': 'Stock disponible'
            }
        ]
    }
    
    return test_data

if __name__ == "__main__":
    # Test de la génération PDF
    test_data = test_pdf_generation()
    generator = BTPDFGenerator()
    pdf_buffer = generator.generate_pdf(test_data)
    
    with open("test_bt.pdf", "wb") as f:
        f.write(pdf_buffer.getvalue())
    
    print("PDF de test généré: test_bt.pdf")
