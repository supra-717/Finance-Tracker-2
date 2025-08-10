from flask import Flask, render_template, request, json
from datetime import datetime
import api_client
import prediction_engine
from config import MAJOR_LEAGUES, CURRENT_SEASON, BOOKMAKER_ID

app = Flask(__name__)

# Permet d'utiliser `tojson` dans les templates
app.jinja_env.filters['tojson'] = json.dumps

@app.route('/')
def index():
    """Affiche la page d'accueil avec le formulaire de sélection."""
    # Trie les ligues par ordre alphabétique pour un affichage propre
    sorted_leagues = dict(sorted(MAJOR_LEAGUES.items()))
    return render_template('index.html', leagues=sorted_leagues)

@app.route('/fixtures', methods=['POST'])
def show_fixtures():
    """Affiche les matchs pour la ligue et la date sélectionnées."""
    league_id = request.form['league_id']
    date_str = request.form['date']

    fixtures_data = api_client.get_fixtures_for_date(date_str, league_id, CURRENT_SEASON)

    fixtures = []
    if fixtures_data and fixtures_data.get('response'):
        fixtures = fixtures_data['response']

    return render_template('fixtures.html', fixtures=fixtures, date=date_str)

@app.route('/result', methods=['POST'])
def show_result():
    """Calcule et affiche la prédiction et les cotes pour un match."""
    # On récupère les données du match, qui ont été passées en JSON
    fixture_data_str = request.form['fixture_data']
    fixture = json.loads(fixture_data_str)

    # 1. Obtenir la prédiction de notre moteur
    prediction = prediction_engine.predict_match(fixture)

    # 2. Obtenir les cotes de Bet365
    odds_data = api_client.get_odds(fixture['fixture']['id'], BOOKMAKER_ID)

    parsed_odds = None
    if odds_data and odds_data.get('response'):
        try:
            bookmaker = odds_data['response'][0]['bookmakers'][0]
            for bet in bookmaker['bets']:
                if bet['name'] == 'Match Winner':
                    parsed_odds = {
                        'home': next((o['odd'] for o in bet['values'] if o['value'] == 'Home'), 'N/A'),
                        'draw': next((o['odd'] for o in bet['values'] if o['value'] == 'Draw'), 'N/A'),
                        'away': next((o['odd'] for o in bet['values'] if o['value'] == 'Away'), 'N/A'),
                    }
                    break
        except (IndexError, KeyError):
            # Les cotes n'ont pas pu être parsées, on laisse parsed_odds à None
            pass

    return render_template('result.html', fixture=fixture, prediction=prediction, odds=parsed_odds)

if __name__ == '__main__':
    # Pour lancer l'application en local :
    # 1. Dans le terminal, exécutez `export FLASK_APP=app.py`
    # 2. Puis `export FLASK_ENV=development` (pour le mode debug)
    # 3. Enfin `flask run`
    app.run(host='0.0.0.0', port=5001, debug=True)
