# Système de Prédiction de Paris Sportifs Football

Ce projet est une **application web** conçue pour prédire les résultats de matchs de football et afficher les cotes, le tout accessible depuis un navigateur, y compris sur smartphone.

## 🏆 Compétition
Ce projet a été réalisé par Jules, une IA ingénieure logicielle, dans le cadre d'une compétition amicale avec ChatGPT pour créer le meilleur et le plus complet des systèmes de prédiction.

## ✨ Fonctionnalités
- **Interface Web Adaptée Mobile** : Une interface simple et claire, utilisable sur n'importe quel appareil doté d'un navigateur web.
- **Modèle de Prédiction v1.0** : Prédiction de matchs basée sur une analyse pondérée de la **forme** récente des équipes et de l'historique des **confrontations directes (H2H)**.
- **Affichage des Cotes** : Intègre et affiche les cotes du bookmaker Bet365 pour chaque match analysé.
- **Transparence** : Le programme affiche les scores de forme et H2H calculés pour que l'utilisateur comprenne la logique derrière chaque prédiction.
- **Structure Modulaire** : Le code est organisé en modules clairs (`api_client`, `prediction_engine`, `app.py`), ce qui le rend facile à maintenir et à améliorer.

## 🚀 Instructions d'Installation et d'Utilisation

Suivez ces 3 étapes simples pour lancer l'application.

### 1. Configurez votre Clé API

L'accès à l'API `api-football` nécessite une clé personnelle.

1.  Ouvrez le fichier `config.py`.
2.  À l'intérieur, trouvez la ligne `API_KEY = "VOTRE_CLE_API"`.
3.  Remplacez `"VOTRE_CLE_API"` par votre clé personnelle que vous pouvez obtenir sur [RapidAPI](https://rapidapi.com/api-sports/api/api-football).

### 2. Installez les Dépendances

Ce projet utilise des librairies Python externes. Pour les installer, ouvrez un terminal dans le répertoire du projet et exécutez la commande suivante :
```bash
pip install -r requirements.txt
```
(Cela installera `requests` et `Flask`).

### 3. Lancez l'Application Web

Une fois la configuration et l'installation terminées, lancez le serveur web.

1.  Ouvrez un terminal dans le répertoire du projet.
2.  Exécutez la commande suivante :
    ```bash
    python app.py
    ```
3.  Le terminal affichera une adresse, probablement `http://127.0.0.1:5001`. Ouvrez cette adresse dans votre navigateur web pour utiliser l'application.
    *(Pour un usage sur smartphone, si votre téléphone est sur le même réseau WiFi que l'ordinateur qui lance le serveur, vous pourrez accéder à l'application en utilisant l'adresse IP locale de l'ordinateur, par exemple `http://192.168.1.XX:5001`)*

## 💡 Améliorations Futures Possibles
Ce projet est une base solide. Voici quelques pistes pour le rendre encore meilleur :
- **Intégrer plus de données** : Classements, statistiques détaillées des joueurs, informations sur les blessés et suspendus.
- **Affiner l'algorithme** : Utiliser des modèles statistiques plus avancés ou du Machine Learning.
- **Déploiement Cloud** : Héberger l'application sur un service cloud pour qu'elle soit accessible de n'importe où, sans avoir à lancer le serveur localement.
