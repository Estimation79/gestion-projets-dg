# utils/formatting.py
"""
Utilitaires de formatage pour l'ERP Production DG Inc.
"""

import re
from math import gcd
from fractions import Fraction


def format_currency(value):
    """Formate une valeur en devise (CAD)"""
    if value is None:
        return "$0.00"
    
    try:
        s_value = str(value).replace(' ', '').replace('€', '').replace('$', '')
        
        # Gestion des séparateurs de milliers
        if ',' in s_value and ('.' not in s_value or s_value.find(',') > s_value.find('.')):
            s_value = s_value.replace('.', '').replace(',', '.')
        elif ',' in s_value and '.' in s_value and s_value.find('.') > s_value.find(','):
            s_value = s_value.replace(',', '')

        num_value = float(s_value)
        if num_value == 0:
            return "$0.00"
        return f"${num_value:,.2f}"
        
    except (ValueError, TypeError):
        if isinstance(value, (int, float)):
            return f"${value:,.2f}"
        return str(value) + " $ (Err)"


def convertir_pieds_pouces_fractions_en_valeur_decimale(mesure_imperiale_str_input):
    """Convertit une mesure impériale en valeur décimale"""
    try:
        mesure_str_cleaned = str(mesure_imperiale_str_input).strip().lower()
        mesure_str_cleaned = mesure_str_cleaned.replace('"', '"').replace("''", "'")
        mesure_str_cleaned = mesure_str_cleaned.replace('ft', "'").replace('pieds', "'").replace('pied', "'")
        mesure_str_cleaned = mesure_str_cleaned.replace('in', '"').replace('pouces', '"').replace('pouce', '"')
        
        if mesure_str_cleaned == "0":
            return 0.0
        
        total_pieds_dec = 0.0
        
        # Pattern pour pieds, pouces et fractions
        pattern_general = re.compile(
            r"^\s*(?:(?P<feet>\d+(?:\.\d+)?)\s*(?:'|\sft|\spieds?)?)?"
            r"\s*(?:(?P<inches>\d+(?:\.\d+)?)\s*(?:\"|\sin|\spouces?)?)?"
            r"\s*(?:(?P<frac_num>\d+)\s*\/\s*(?P<frac_den>\d+)\s*(?:\"|\sin|\spouces?)?)?\s*$"
        )
        
        # Pattern pour nombres seulement
        pattern_nombres_seulement = re.compile(
            r"^\s*(?P<num1>\d+(?:\.\d+)?)"
            r"(?:\s+(?P<num2>\d+(?:\.\d+)?)"
            r"(?:\s+(?P<frac_num2>\d+)\s*\/\s*(?P<frac_den2>\d+))?"
            r")?"
            r"(?:\s+(?P<frac_num1>\d+)\s*\/\s*(?P<frac_den1>\d+))?"
            r"\s*$"
        )
        
        match = pattern_general.match(mesure_str_cleaned)
        pieds_val, pouces_val, fraction_dec = 0.0, 0.0, 0.0
        
        if match and (match.group('feet') or match.group('inches') or match.group('frac_num')):
            if match.group('feet'):
                pieds_val = float(match.group('feet'))
            if match.group('inches'):
                pouces_val = float(match.group('inches'))
            if match.group('frac_num') and match.group('frac_den'):
                num, den = int(match.group('frac_num')), int(match.group('frac_den'))
                if den == 0:
                    return 0.0
                fraction_dec = num / den
        else:
            match_alt = pattern_nombres_seulement.match(mesure_str_cleaned)
            if match_alt:
                pieds_val = float(match_alt.group('num1'))
                if match_alt.group('num2'):
                    pouces_val = float(match_alt.group('num2'))
                    if match_alt.group('frac_num2') and match_alt.group('frac_den2'):
                        num, den = int(match_alt.group('frac_num2')), int(match_alt.group('frac_den2'))
                        if den == 0:
                            return 0.0
                        fraction_dec = num / den
                elif match_alt.group('frac_num1') and match_alt.group('frac_den1'):
                    num, den = int(match_alt.group('frac_num1')), int(match_alt.group('frac_den1'))
                    if den == 0:
                        return 0.0
                    pouces_val = num / den
            elif "/" in mesure_str_cleaned:
                try:
                    pouces_val = float(Fraction(mesure_str_cleaned))
                except ValueError:
                    return 0.0
            elif mesure_str_cleaned.replace('.', '', 1).isdigit():
                try:
                    pouces_val = float(mesure_str_cleaned)
                except ValueError:
                    return 0.0
            else:
                return 0.0
        
        total_pieds_dec = pieds_val + (pouces_val / 12.0) + (fraction_dec / 12.0)
        return total_pieds_dec
        
    except Exception:
        return 0.0


def convertir_en_pieds_pouces_fractions(valeur_decimale_pieds_input):
    """Convertit une valeur décimale en format pieds-pouces-fractions"""
    try:
        valeur_pieds_dec = float(valeur_decimale_pieds_input)
        if valeur_pieds_dec < 0:
            valeur_pieds_dec = 0
        
        pieds_entiers = int(valeur_pieds_dec)
        pouces_decimaux_restants_total = (valeur_pieds_dec - pieds_entiers) * 12.0
        pouces_entiers = int(pouces_decimaux_restants_total)
        fraction_decimale_de_pouce = pouces_decimaux_restants_total - pouces_entiers
        
        fraction_denominateur = 8
        fraction_numerateur_arrondi = round(fraction_decimale_de_pouce * fraction_denominateur)
        fraction_display_str = ""
        
        if fraction_numerateur_arrondi > 0:
            if fraction_numerateur_arrondi == fraction_denominateur:
                pouces_entiers += 1
            else:
                common_divisor = gcd(fraction_numerateur_arrondi, fraction_denominateur)
                num_simplifie = fraction_numerateur_arrondi // common_divisor
                den_simplifie = fraction_denominateur // common_divisor
                fraction_display_str = f" {num_simplifie}/{den_simplifie}"
        
        if pouces_entiers >= 12:
            pieds_entiers += pouces_entiers // 12
            pouces_entiers %= 12
        
        if pieds_entiers == 0 and pouces_entiers == 0 and not fraction_display_str:
            return "0' 0\""
        
        return f"{pieds_entiers}' {pouces_entiers}{fraction_display_str}\""
        
    except Exception:
        return "0' 0\""


def valider_mesure_saisie(mesure_saisie_str):
    """Valide et standardise une mesure saisie"""
    mesure_nettoyee = str(mesure_saisie_str).strip()
    if not mesure_nettoyee:
        return True, "0' 0\""
    
    try:
        valeur_pieds_dec = convertir_pieds_pouces_fractions_en_valeur_decimale(mesure_nettoyee)
        entree_est_zero_explicite = mesure_nettoyee in ["0", "0'", "0\"", "0.0", "0.0'"]
        
        if valeur_pieds_dec > 0.000001 or entree_est_zero_explicite:
            format_standardise = convertir_en_pieds_pouces_fractions(valeur_pieds_dec)
            return True, format_standardise
        else:
            return False, f"Format non reconnu ou invalide: '{mesure_nettoyee}'"
            
    except Exception as e_valid:
        return False, f"Erreur de validation: {e_valid}"


def convertir_imperial_vers_metrique(mesure_imperiale_str_conv):
    """Convertit une mesure impériale en métrique"""
    try:
        valeur_pieds_decimaux_conv = convertir_pieds_pouces_fractions_en_valeur_decimale(mesure_imperiale_str_conv)
        metres_val = valeur_pieds_decimaux_conv * 0.3048
        return {"valeur": round(metres_val, 3), "unite": "m"}
    except Exception:
        return {"valeur": 0.0, "unite": "m"}


def format_duration(hours):
    """Formate une durée en heures"""
    if hours is None or hours == 0:
        return "0h"
    
    try:
        hours_float = float(hours)
        if hours_float < 1:
            minutes = int(hours_float * 60)
            return f"{minutes}min"
        elif hours_float.is_integer():
            return f"{int(hours_float)}h"
        else:
            return f"{hours_float:.1f}h"
    except (ValueError, TypeError):
        return str(hours)


def format_percentage(value):
    """Formate un pourcentage"""
    if value is None:
        return "0%"
    
    try:
        return f"{float(value):.1f}%"
    except (ValueError, TypeError):
        return str(value)


def truncate_string(text, max_length=50, suffix="..."):
    """Tronque une chaîne de caractères"""
    if not text:
        return ""
    
    text_str = str(text)
    if len(text_str) <= max_length:
        return text_str
    
    return text_str[:max_length - len(suffix)] + suffix
