# run_migration.py - Script Principal Migration ERP Production DG Inc.
# Exécution complète de la migration JSON → SQLite

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Import des modules de migration
from erp_database import ERPDatabase
from migration_scripts import MigrationManager, validate_migration_results
from test_migration import run_performance_test

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def print_banner():
    """Affiche la bannière ERP Production DG Inc."""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║               🏭 ERP Production DG Inc.                      ║
    ║                 Migration JSON → SQLite                      ║
    ║                                                              ║
    ║         Transformation vers Architecture Unifiée            ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_prerequisites() -> bool:
    """Vérifie les prérequis pour la migration"""
    logger.info("🔍 Vérification des prérequis...")
    
    issues = []
    
    # Vérifier fichiers JSON source
    required_files = {
        'projets_data.json': 'Données projets ERP',
        'crm_data.json': 'Données CRM',
        'employees_data.json': 'Données employés',
        'inventaire_v2.json': 'Données inventaire'
    }
    
    for file, description in required_files.items():
        if not os.path.exists(file):
            issues.append(f"❌ {file} manquant ({description})")
        else:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"✅ {file} trouvé et valide")
            except json.JSONDecodeError as e:
                issues.append(f"❌ {file} invalide: {e}")
    
    # Vérifier module postes_travail
    try:
        from postes_travail import WORK_CENTERS_DG_INC
        if len(WORK_CENTERS_DG_INC) == 61:
            logger.info("✅ Module postes_travail disponible (61 postes)")
        else:
            issues.append(f"❌ Postes de travail incorrects: {len(WORK_CENTERS_DG_INC)} au lieu de 61")
    except ImportError:
        issues.append("❌ Module postes_travail.py manquant")
    
    # Vérifier espace disque
    free_space = os.statvfs('.').f_frsize * os.statvfs('.').f_availif hasattr(os, 'statvfs') else float('inf')
    if free_space < 100 * 1024 * 1024:  # 100MB minimum
        issues.append("❌ Espace disque insuffisant (minimum 100MB)")
    
    if issues:
        logger.error("🚨 Prérequis non satisfaits:")
        for issue in issues:
            logger.error(f"  {issue}")
        return False
    
    logger.info("✅ Tous les prérequis satisfaits")
    return True

def get_migration_plan() -> dict:
    """Retourne le plan de migration détaillé"""
    return {
        'phase_1': {
            'name': 'Préparation',
            'steps': [
                'Création base SQLite avec schéma complet',
                'Sauvegarde fichiers JSON existants',
                'Validation structure données'
            ]
        },
        'phase_2': {
            'name': 'Migration Référentiels',
            'steps': [
                'Migration 61 postes de travail',
                'Migration entreprises CRM',
                'Migration contacts CRM'
            ]
        },
        'phase_3': {
            'name': 'Migration Données Métier',
            'steps': [
                'Migration 21 employés DG Inc.',
                'Migration projets avec opérations',
                'Migration matériaux et BOM'
            ]
        },
        'phase_4': {
            'name': 'Migration Avancée',
            'steps': [
                'Migration inventaire (mesures impériales)',
                'Intégration TimeTracker existant',
                'Création relations et index'
            ]
        },
        'phase_5': {
            'name': 'Validation',
            'steps': [
                'Tests intégrité données',
                'Validation performances',
                'Rapport final'
            ]
        }
    }

def display_migration_plan():
    """Affiche le plan de migration"""
    plan = get_migration_plan()
    
    print("\n📋 PLAN DE MIGRATION:")
    print("=" * 60)
    
    for phase_key, phase in plan.items():
        print(f"\n🔹 {phase['name']} ({phase_key.upper()})")
        for i, step in enumerate(phase['steps'], 1):
            print(f"   {i}. {step}")

def run_interactive_migration():
    """Exécute la migration en mode interactif"""
    print_banner()
    
    # Vérification prérequis
    if not check_prerequisites():
        print("\n❌ Migration impossible - Prérequis non satisfaits")
        return False
    
    # Affichage du plan
    display_migration_plan()
    
    # Confirmation utilisateur
    print(f"\n{'='*60}")
    print("⚠️  ATTENTION: Cette migration va:")
    print("   • Créer une nouvelle base SQLite unifiée")
    print("   • Sauvegarder automatiquement vos fichiers JSON")
    print("   • Transformer l'architecture de votre ERP")
    print(f"{'='*60}")
    
    response = input("\n🤔 Voulez-vous continuer? (oui/non): ").lower().strip()
    if response not in ['oui', 'o', 'yes', 'y']:
        print("❌ Migration annulée par l'utilisateur")
        return False
    
    # Exécution migration
    return execute_migration()

def execute_migration() -> bool:
    """Exécute la migration complète"""
    logger.info("🚀 DÉBUT MIGRATION COMPLÈTE")
    start_time = datetime.now()
    
    try:
        # Initialisation
        db = ERPDatabase("erp_production_dg.db")
        migration_manager = MigrationManager(db)
        
        print("\n" + "="*60)
        print("🔄 EXÉCUTION MIGRATION EN COURS...")
        print("="*60)
        
        # Exécution migration
        results = migration_manager.run_full_migration()
        
        # Affichage résultats par module
        print(f"\n📊 RÉSULTATS PAR MODULE:")
        print("-" * 40)
        
        total_migrated = 0
        failed_modules = []
        
        for module_name, module_result in results.get('modules', {}).items():
            if module_result.get('success'):
                count = module_result.get('migrated_count', 0)
                if isinstance(count, dict):
                    # Pour CRM qui a plusieurs compteurs
                    total_count = sum(count.values())
                    detail = ", ".join([f"{k}:{v}" for k, v in count.items()])
                    print(f"✅ {module_name:15} - {total_count:3} enregistrements ({detail})")
                    total_migrated += total_count
                else:
                    print(f"✅ {module_name:15} - {count:3} enregistrements")
                    total_migrated += count
            else:
                error = module_result.get('error', 'Erreur inconnue')
                print(f"❌ {module_name:15} - ÉCHEC: {error}")
                failed_modules.append(module_name)
        
        # Tests de validation
        print(f"\n🔍 VALIDATION POST-MIGRATION:")
        print("-" * 40)
        
        validation_results = validate_migration_results(db)
        
        # Affichage compteurs finaux
        table_counts = validation_results['table_counts']
        for table, count in table_counts.items():
            print(f"📊 {table:20} - {count:4} enregistrements")
        
        # Tests d'intégrité
        integrity_checks = validation_results['integrity_checks']
        integrity_ok = all(integrity_checks.values())
        
        if integrity_ok:
            print("✅ Intégrité des données validée")
        else:
            print("⚠️  Problèmes d'intégrité détectés:")
            for check, status in integrity_checks.items():
                if not status:
                    print(f"   ❌ {check}")
        
        # Test performance
        print(f"\n⚡ TEST PERFORMANCE:")
        print("-" * 40)
        perf_results = run_performance_test(db)
        for test_name, time_taken in perf_results.items():
            print(f"🕒 {test_name:20} - {time_taken:.4f}s")
        
        # Résumé final
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n{'='*60}")
        print("📋 RÉSUMÉ FINAL")
        print("="*60)
        print(f"🕒 Durée totale:        {duration}")
        print(f"📊 Total migré:         {total_migrated} enregistrements")
        print(f"📁 Taille base finale:  {validation_results['schema_info']['file_size_mb']} MB")
        
        if failed_modules:
            print(f"⚠️  Modules échoués:      {', '.join(failed_modules)}")
            print("🔧 Recommandation:      Vérifier logs pour détails")
        
        if results.get('success') and integrity_ok and not failed_modules:
            print("\n🎉 MIGRATION RÉUSSIE!")
            print("✅ Votre ERP est maintenant unifié sur SQLite")
            print("🚀 Prêt pour la Phase 2 du développement")
            
            # Instructions suite
            print(f"\n📝 PROCHAINES ÉTAPES:")
            print("1. Modifier app.py pour utiliser ERPDatabase")
            print("2. Adapter les modules CRM, employees, etc.")
            print("3. Tester interface Streamlit complète")
            print("4. Supprimer database_sync.py devenu obsolète")
            
            return True
        else:
            print("\n⚠️  MIGRATION PARTIELLEMENT RÉUSSIE")
            print("🔧 Vérifier les logs pour résoudre les problèmes")
            return False
    
    except Exception as e:
        logger.error(f"❌ Erreur critique migration: {e}")
        print(f"\n💥 ERREUR CRITIQUE: {e}")
        print("🔧 Consultez migration.log pour détails")
        return False

def run_automated_migration():
    """Exécute la migration en mode automatique (sans interaction)"""
    print_banner()
    logger.info("🤖 Mode automatique - Début migration")
    
    if not check_prerequisites():
        logger.error("❌ Prérequis non satisfaits")
        return False
    
    return execute_migration()

def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description='Migration ERP Production DG Inc. - JSON vers SQLite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python run_migration.py                    # Mode interactif
  python run_migration.py --auto             # Mode automatique
  python run_migration.py --check-only       # Vérification uniquement
  python run_migration.py --plan             # Afficher plan seulement
        """
    )
    
    parser.add_argument('--auto', action='store_true', 
                       help='Mode automatique sans interaction')
    parser.add_argument('--check-only', action='store_true',
                       help='Vérifier prérequis uniquement')
    parser.add_argument('--plan', action='store_true',
                       help='Afficher plan de migration uniquement')
    
    args = parser.parse_args()
    
    if args.plan:
        print_banner()
        display_migration_plan()
        return
    
    if args.check_only:
        print_banner()
        success = check_prerequisites()
        sys.exit(0 if success else 1)
    
    # Exécution migration
    if args.auto:
        success = run_automated_migration()
    else:
        success = run_interactive_migration()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
