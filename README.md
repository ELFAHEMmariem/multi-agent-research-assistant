Multi-Agent Research Assistant
Un assistant de recherche autonome et distribué basé sur une architecture multi-agents orchestrée avec LangGraph, exécuté via des microservices asynchrones FastAPI et Redis, et appuyé par des modèles de langage haute performance Groq ainsi que la recherche web en temps réel Tavily AI.

Architecture du Système
Le projet repose sur une orchestration par graphes d'états où plusieurs agents spécialisés collaborent pour produire des synthèses détaillées.

Planner Agent : Analyse la question initiale et la découpe en sous-questions optimisées.

Researcher Agent : Interroge l'API Tavily pour collecter des sources web pertinentes et filtrer l'information.

Writer Agent : Syntétise les résultats et rédige un rapport structuré au format Markdown.

Tech Stack
Framework API : FastAPI pour l'exécution asynchrone et le streaming Server-Sent Events.

Orchestration d'Agents : LangGraph et LangChain.

Modèles de Langage : API Groq Cloud avec les modèles Qwen 3.8 27B et GPT OSS 20B.

Recherche Web : Tavily AI.

Gestion d'État et Stockage : Redis en conteneur Docker.

Validation des Données : Pydantic v2 et Pydantic-Settings.

Endpoints API Disponibles
POST /research : Initie une nouvelle recherche en arrière-plan et retourne un identifiant unique de suivi.

GET /research/{run_id} : Récupère le statut d'exécution (en cours, terminé, échoué) et le rapport final.

GET /research/{run_id}/stream : Flux SSE pour suivre la progression des agents en temps réel.

GET /research/{run_id}/trace : Permet d'inspecter les étapes et le comportement du graphe d'agents.

GET /health : Vérifie l'état de santé de l'API et des connexions aux services tiers.

Acquis Techniques du Projet
Architecture Multi-Agents : Conception de workflows sous forme de graphes d'état décisionnels.

Programmation Asynchrone : Traitement des tâches lourdes en arrière-plan sans bloquer les requêtes HTTP.

Communication en Temps Réel : Transmission continue des logs d'agents au client via streaming.

Persistance d'État : Utilisation d'une base clé-valeur en mémoire pour gérer le cycle de vie des exécutions.
