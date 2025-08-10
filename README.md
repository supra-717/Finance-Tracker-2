# Système de Prédiction Automatisé pour le Football

Ce projet est un **système automatisé** qui utilise GitHub Actions pour générer quotidiennement des prédictions de matchs de football. Il n'y a pas d'interface web ; tout est géré par des workflows automatisés directement dans GitHub.

## 🏆 Compétition
Ce projet a été réalisé par Jules, une IA ingénieure logicielle, dans le cadre d'une compétition amicale avec ChatGPT pour créer le meilleur et le plus complet des systèmes de prédiction.

## ✨ Fonctionnalités
- **Automatisation Complète** : Le système s'exécute automatiquement chaque jour pour récupérer les prédictions des matchs à venir.
- **Déclenchement Manuel** : En plus de l'automatisation, vous pouvez lancer le processus de prédiction à tout moment d'un simple clic.
- **Modèle de Prédiction v1.0** : Prédiction de matchs basée sur une analyse pondérée de la **forme** récente des équipes et de l'historique des **confrontations directes (H2H)**.
- **Intégration des Cotes** : Récupère et affiche les cotes du bookmaker Bet365 pour chaque match.
- **Utilisation Sécurisée de l'API** : La clé API est stockée de manière sécurisée grâce aux Secrets de GitHub.

## 🚀 Workflow d'Utilisation

Le fonctionnement est maintenant basé sur les "Actions" de GitHub. Voici comment l'utiliser.

### Étape 1 : Configuration de la Clé API (Une seule fois)

C'est l'étape la plus importante. Pour que le système puisse fonctionner, vous devez fournir votre clé API de manière sécurisée.

1.  Dans votre dépôt GitHub, allez dans l'onglet **Settings** (Paramètres).
2.  Dans le menu de gauche, naviguez jusqu'à **Secrets and variables** > **Actions**.
3.  Cliquez sur le bouton **New repository secret**.
4.  Pour le **Name** (Nom), entrez exactement `API_FOOTBALL_KEY`. C'est très important que le nom soit identique.
5.  Pour le **Secret**, collez votre clé API personnelle que vous avez obtenue sur RapidAPI.
6.  Cliquez sur **Add secret**.

Votre clé est maintenant stockée de manière sécurisée.

### Étape 2 : Lancer les Prédictions

Vous avez deux options :

**Option A : Attendre l'exécution automatique**
- Le système est programmé pour s'exécuter **tous les jours à 8h00 UTC**. Vous n'avez rien à faire, les prédictions seront générées automatiquement.

**Option B : Lancer manuellement**
1.  Allez dans l'onglet **Actions** de votre dépôt GitHub.
2.  Dans le menu de gauche, cliquez sur le workflow nommé **"Daily Football Predictions"**.
3.  Vous verrez un message "This workflow has a workflow_dispatch event". Cliquez sur le bouton **Run workflow** à droite.
4.  Laissez les options par défaut et cliquez sur le bouton vert **Run workflow**.

### Étape 3 : Voir les Résultats

1.  Toujours dans l'onglet **Actions**, vous verrez une nouvelle ligne apparaître pour l'exécution que vous venez de lancer (ou pour l'exécution quotidienne).
2.  Cliquez sur le titre de cette exécution.
3.  Sur la page suivante, cliquez sur la tâche nommée **"build"**.
4.  Les logs (le compte-rendu) de l'exécution s'afficheront. Déroulez la section **"Run prediction script"** pour voir la liste de toutes les prédictions générées.
