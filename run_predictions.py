import datetime
import api_client
import prediction_engine
from config import CURRENT_SEASON, BOOKMAKER_ID

# Liste des championnats à analyser
# Pourrait être mise dans config.py, mais la garder ici est aussi simple.
LEAGUES_TO_CHECK = {
    "Premier League": 39,
    "Ligue 1": 61,
    "La Liga": 140,
    "Serie A": 135,
    "Bundesliga": 78,
    "UEFA Champions League": 2,
    "UEFA Europa League": 3,
}

def main():
    """
    Script principal pour générer et afficher les prédictions du jour.
    """
    today_str = datetime.datetime.now().strftime('%Y-%m-%d')
    print(f"--- Prédictions pour le {today_str} ---\n")

    found_any_match = False

    for league_name, league_id in LEAGUES_TO_CHECK.items():
        print(f"--- Championnat : {league_name} ---")

        fixtures_data = api_client.get_fixtures_for_date(today_str, league_id, CURRENT_SEASON)

        if not fixtures_data or not fixtures_data.get('response'):
            print("Pas de matchs aujourd'hui.\n")
            continue

        fixtures = fixtures_data['response']
        found_any_match = True

        for fixture in fixtures:
            home_team = fixture['teams']['home']['name']
            away_team = fixture['teams']['away']['name']
            print(f"\nMatch : {home_team} vs {away_team}")

            # 1. Prédiction
            prediction = prediction_engine.predict_match(fixture)
            print(f"  -> Prédiction Jules : {prediction}")

            # 2. Cotes
            odds_data = api_client.get_odds(fixture['fixture']['id'], BOOKMAKER_ID)
            if odds_data and odds_data.get('response'):
                try:
                    bookmaker = odds_data['response'][0]['bookmakers'][0]
                    winner_odds = next((b for b in bookmaker['bets'] if b['name'] == 'Match Winner'), None)
                    if winner_odds:
                        home = next((o['odd'] for o in winner_odds['values'] if o['value'] == 'Home'), 'N/A')
                        draw = next((o['odd'] for o in winner_odds['values'] if o['value'] == 'Draw'), 'N/A')
                        away = next((o['odd'] for o in winner_odds['values'] if o['value'] == 'Away'), 'N/A')
                        print(f"  -> Cotes Bet365   : Domicile({home}) Nul({draw}) Extérieur({away})")
                    else:
                        print("  -> Cotes 'Match Winner' non trouvées.")
                except (IndexError, KeyError):
                    print("  -> Impossible de parser les cotes.")
            else:
                print("  -> Cotes non disponibles.")

        print("\n-----------------------------------\n")

    if not found_any_match:
        print("Aucun match trouvé pour les championnats surveillés aujourd'hui.")

if __name__ == "__main__":
    # Note: Le 'prediction_engine' a ses propres `print` pour détailler le calcul.
    # Pour le log final de l'action, on pourrait vouloir les désactiver pour plus de clarté.
    # Pour l'instant, on les garde pour le debug.
    main()
