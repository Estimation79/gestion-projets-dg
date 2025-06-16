# cache_config.py - Configuration et monitoring du cache
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os

class CacheOptimizer:
   """Optimiseur de cache pour l'API Anthropic avec prompt caching."""
   
   def __init__(self, config_file="cache_config.json"):
       self.config_file = config_file
       self.cache_stats = {
           "session_start": datetime.now().isoformat(),
           "total_requests": 0,
           "cache_hits": 0,
           "cache_misses": 0,
           "total_tokens_saved": 0,
           "total_cost_saved": 0.0,
           "avg_response_time_cached": 0.0,
           "avg_response_time_uncached": 0.0,
           "cache_hit_rate": 0.0,
           "recommendations": []
       }
       self.load_config()
   
   def load_config(self):
       """Charge la configuration depuis le fichier."""
       default_config = {
           "cache_strategies": {
               "system_prompts": {
                   "ttl": "1h",  # Instructions de base réutilisées fréquemment
                   "threshold_tokens": 500
               },
               "document_content": {
                   "ttl": "5m",  # Contenu de document pour analyse
                   "threshold_tokens": 1024
               },
               "conversation_history": {
                   "ttl": "5m",  # Historique de conversation
                   "threshold_tokens": 2048,
                   "max_turns": 20
               },
               "technical_instructions": {
                   "ttl": "1h",  # Instructions techniques spécialisées
                   "threshold_tokens": 800
               }
           },
           "optimization_rules": {
               "min_cache_size": 1024,  # Taille minimum pour activer le cache
               "max_context_length": 100000,  # Limite du contexte total
               "cache_efficiency_threshold": 0.3,  # Seuil d'efficacité minimum
               "auto_adjust_ttl": True
           },
           "monitoring": {
               "log_cache_performance": True,
               "detailed_stats": True,
               "alert_on_low_efficiency": True,
               "efficiency_threshold": 0.2
           }
       }
       
       try:
           if os.path.exists(self.config_file):
               with open(self.config_file, 'r', encoding='utf-8') as f:
                   self.config = json.load(f)
           else:
               self.config = default_config
               self.save_config()
       except Exception as e:
           print(f"Erreur chargement config cache: {e}")
           self.config = default_config
   
   def save_config(self):
       """Sauvegarde la configuration."""
       try:
           with open(self.config_file, 'w', encoding='utf-8') as f:
               json.dump(self.config, f, indent=2, ensure_ascii=False)
       except Exception as e:
           print(f"Erreur sauvegarde config cache: {e}")
   
   def get_optimal_cache_strategy(self, content_type: str, content_length: int, 
                                conversation_length: int = 0) -> Dict:
       """Détermine la stratégie de cache optimale."""
       
       strategies = self.config["cache_strategies"]
       rules = self.config["optimization_rules"]
       
       # Pas de cache si trop petit
       if content_length < rules["min_cache_size"]:
           return {"use_cache": False, "reason": "Content too small"}
       
       # Sélection de la stratégie selon le type de contenu
       if content_type in strategies:
           strategy = strategies[content_type].copy()
           
           # Ajustement TTL selon la longueur de conversation
           if content_type == "conversation_history" and conversation_length > 10:
               strategy["ttl"] = "1h"  # Cache plus long pour longues conversations
           
           # Ajustement selon la taille du contenu
           if content_length > 10000:  # Gros contenu
               if strategy["ttl"] == "5m":
                   strategy["ttl"] = "1h"  # Prolonger le cache
           
           strategy["use_cache"] = content_length >= strategy["threshold_tokens"]
           return strategy
       
       # Stratégie par défaut
       return {
           "use_cache": content_length >= 1024,
           "ttl": "5m",
           "threshold_tokens": 1024
       }
   
   def record_cache_hit(self, tokens_read: int, response_time: float):
       """Enregistre un hit de cache."""
       self.cache_stats["cache_hits"] += 1
       self.cache_stats["total_tokens_saved"] += tokens_read
       self.cache_stats["total_requests"] += 1
       
       # Calcul du coût économisé (Claude Sonnet 4: cache read = $0.30/MTok vs input = $3/MTok)
       cost_saved = (tokens_read / 1000000) * (3.0 - 0.30)
       self.cache_stats["total_cost_saved"] += cost_saved
       
       # Mise à jour temps de réponse moyen
       current_avg = self.cache_stats["avg_response_time_cached"]
       hits = self.cache_stats["cache_hits"]
       self.cache_stats["avg_response_time_cached"] = ((current_avg * (hits - 1)) + response_time) / hits
       
       self._update_hit_rate()
   
   def record_cache_miss(self, tokens_created: int, response_time: float):
       """Enregistre un miss de cache."""
       self.cache_stats["cache_misses"] += 1
       self.cache_stats["total_requests"] += 1
       
       # Mise à jour temps de réponse moyen
       current_avg = self.cache_stats["avg_response_time_uncached"]
       misses = self.cache_stats["cache_misses"]
       self.cache_stats["avg_response_time_uncached"] = ((current_avg * (misses - 1)) + response_time) / misses
       
       self._update_hit_rate()
   
   def _update_hit_rate(self):
       """Met à jour le taux de hit du cache."""
       total = self.cache_stats["total_requests"]
       if total > 0:
           self.cache_stats["cache_hit_rate"] = self.cache_stats["cache_hits"] / total
   
   def get_performance_report(self) -> Dict:
       """Génère un rapport de performance du cache."""
       stats = self.cache_stats.copy()
       
       # Calculer les économies
       if stats["total_requests"] > 0:
           efficiency = stats["cache_hit_rate"]
           
           # Estimations de performance
           if stats["avg_response_time_cached"] > 0 and stats["avg_response_time_uncached"] > 0:
               time_improvement = ((stats["avg_response_time_uncached"] - stats["avg_response_time_cached"]) / 
                                 stats["avg_response_time_uncached"]) * 100
               stats["time_improvement_percent"] = round(time_improvement, 2)
           
           # Recommandations
           recommendations = []
           
           if efficiency < 0.3:
               recommendations.append("Taux de cache faible. Considérez augmenter les TTL ou ajuster les seuils.")
           elif efficiency > 0.7:
               recommendations.append("Excellent taux de cache! Continuez avec la stratégie actuelle.")
           
           if stats["total_cost_saved"] > 1.0:
               recommendations.append(f"Économies significatives: ${stats['total_cost_saved']:.2f}")
           
           if stats["total_tokens_saved"] > 100000:
               recommendations.append(f"Tokens économisés: {stats['total_tokens_saved']:,}")
           
           stats["recommendations"] = recommendations
       
       return stats
   
   def optimize_based_on_usage(self):
       """Optimise automatiquement la configuration selon l'usage."""
       stats = self.cache_stats
       config_updated = False
       
       if stats["total_requests"] < 10:
           return  # Pas assez de données
       
       hit_rate = stats["cache_hit_rate"]
       
       # Ajustement automatique des TTL
       if self.config["optimization_rules"]["auto_adjust_ttl"]:
           if hit_rate < 0.2:  # Faible taux de hit
               # Augmenter les TTL
               for strategy in self.config["cache_strategies"].values():
                   if strategy["ttl"] == "5m":
                       strategy["ttl"] = "1h"
                       config_updated = True
           elif hit_rate > 0.8:  # Très bon taux de hit
               # Possibilité de réduire certains seuils
               for strategy in self.config["cache_strategies"].values():
                   if strategy["threshold_tokens"] > 1024:
                       strategy["threshold_tokens"] = max(1024, strategy["threshold_tokens"] - 256)
                       config_updated = True
       
       if config_updated:
           self.save_config()
           print("[CACHE] Configuration optimisée automatiquement")
   
   def should_use_extended_cache(self, usage_pattern: str) -> bool:
       """Détermine si le cache étendu (1h) doit être utilisé."""
       patterns_for_extended = [
           "long_conversation",  # Conversations longues
           "document_analysis",  # Analyse de documents volumineux
           "technical_drawing",  # Dessins techniques (réutilisation probable)
           "system_prompts"      # Instructions système
       ]
       return usage_pattern in patterns_for_extended
   
   def get_cache_health_status(self) -> str:
       """Retourne le statut de santé du cache."""
       hit_rate = self.cache_stats["cache_hit_rate"]
       
       if hit_rate >= 0.7:
           return "EXCELLENT"
       elif hit_rate >= 0.5:
           return "BON"
       elif hit_rate >= 0.3:
           return "MOYEN"
       else:
           return "FAIBLE"


class CacheMonitor:
   """Moniteur de performance du cache en temps réel."""
   
   def __init__(self):
       self.session_stats = []
       self.start_time = time.time()
   
   def log_request(self, request_type: str, cache_hit: bool, 
                  tokens_processed: int, response_time: float):
       """Enregistre une requête pour monitoring."""
       self.session_stats.append({
           "timestamp": datetime.now().isoformat(),
           "type": request_type,
           "cache_hit": cache_hit,
           "tokens": tokens_processed,
           "response_time": response_time
       })
   
   def get_recent_performance(self, minutes: int = 5) -> Dict:
       """Obtient les performances récentes."""
       cutoff = datetime.now() - timedelta(minutes=minutes)
       
       recent_stats = [
           stat for stat in self.session_stats 
           if datetime.fromisoformat(stat["timestamp"]) > cutoff
       ]
       
       if not recent_stats:
           return {"status": "no_data"}
       
       total_requests = len(recent_stats)
       cache_hits = sum(1 for stat in recent_stats if stat["cache_hit"])
       avg_response_time = sum(stat["response_time"] for stat in recent_stats) / total_requests
       
       return {
           "total_requests": total_requests,
           "cache_hit_rate": cache_hits / total_requests if total_requests > 0 else 0,
           "avg_response_time": avg_response_time,
           "period_minutes": minutes
       }
   
   def export_stats(self, filename: str = None):
       """Exporte les statistiques vers un fichier JSON."""
       if not filename:
           filename = f"cache_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
       
       export_data = {
           "session_start": datetime.fromtimestamp(self.start_time).isoformat(),
           "export_time": datetime.now().isoformat(),
           "total_requests": len(self.session_stats),
           "detailed_stats": self.session_stats
       }
       
       try:
           with open(filename, 'w', encoding='utf-8') as f:
               json.dump(export_data, f, indent=2, ensure_ascii=False)
           print(f"[MONITOR] Statistiques exportées vers {filename}")
       except Exception as e:
           print(f"[MONITOR] Erreur export: {e}")


# Utilitaires pour l'intégration
def create_cache_control(ttl: str = "5m") -> Dict:
   """Crée un bloc cache_control standard."""
   return {"type": "ephemeral", "ttl": ttl}

def estimate_tokens(text: str) -> int:
   """Estimation approximative du nombre de tokens."""
   # Approximation: ~4 caractères par token pour le français/anglais
   return len(text) // 4

def should_cache_content(content: str, min_tokens: int = 1024) -> bool:
   """Détermine si un contenu devrait être caché."""
   return estimate_tokens(content) >= min_tokens
