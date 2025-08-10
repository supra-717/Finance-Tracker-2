import os

# Clé API - LUE DEPUIS LES SECRETS GITHUB (variable d'environnement)
# Pour les tests en local, vous pouvez décommenter la ligne suivante et y mettre votre clé
# API_KEY = "VOTRE_CLE_API"
API_KEY = os.getenv("API_FOOTBALL_KEY")

if not API_KEY:
    raise ValueError("La clé API n'est pas configurée. Veuillez définir le Secret 'API_FOOTBALL_KEY' dans les paramètres de votre dépôt GitHub.")

# URL de base de l'API v3
API_HOST = "api-football-v1.p.rapidapi.com"
BASE_URL = f"https://{API_HOST}/v3"

# ID du bookmaker à utiliser pour les cotes (Bet365)
BOOKMAKER_ID = 8

# Saison actuelle (à mettre à jour si nécessaire)
CURRENT_SEASON = 2023
