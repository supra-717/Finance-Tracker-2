"""
Client pour interagir avec l'API api-football.

Ce module contient les fonctions nécessaires pour effectuer des appels
à l'API, gérer l'authentification et récupérer les données sur
les ligues, équipes, matchs, etc.
"""
import requests
from config import API_KEY, BASE_URL

def get_data(endpoint, params=None):
    """
    Fonction générique pour faire des appels GET à l'API.
    """
    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': "api-football-v1.p.rapidapi.com"
    }

    url = f"{BASE_URL}/{endpoint}"

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de l'appel à l'API : {e}")
        return None

# Fonctions spécifiques pour les endpoints de l'API Football

def get_leagues():
    """Récupère la liste des ligues et pays disponibles."""
    return get_data("leagues")

def get_teams(league_id, season):
    """Récupère les équipes pour une ligue et une saison données."""
    params = {'league': league_id, 'season': season}
    return get_data("teams", params=params)

def get_fixtures_for_date(date_str, league_id, season):
    """Récupère les matchs pour une date, une ligue et une saison données."""
    params = {'date': date_str, 'league': league_id, 'season': season}
    return get_data("fixtures", params=params)

def get_team_statistics(team_id, league_id, season):
    """Récupère les statistiques d'une équipe pour une saison."""
    params = {'team': team_id, 'league': league_id, 'season': season}
    return get_data("teams/statistics", params=params)

def get_head_to_head(team1_id, team2_id):
    """Récupère l'historique des confrontations entre deux équipes."""
    # L'API attend les IDs des équipes séparés par un tiret
    h2h_str = f"{team1_id}-{team2_id}"
    params = {'h2h': h2h_str}
    return get_data("fixtures/headtohead", params=params)

def get_last_n_fixtures(team_id, n=5):
    """Récupère les n derniers matchs d'une équipe."""
    params = {'team': team_id, 'last': n}
    return get_data("fixtures", params=params)

def get_odds(fixture_id, bookmaker_id):
    """Récupère les cotes pour un match et un bookmaker donnés."""
    params = {'fixture': fixture_id, 'bookmaker': bookmaker_id}
    return get_data("odds", params=params)
