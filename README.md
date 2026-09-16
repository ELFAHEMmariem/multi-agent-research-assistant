MULTI-AGENT RESEARCH ASSISTANT
Un assistant de recherche autonome et distribué basé sur une architecture multi-agents orchestrée avec LangGraph, exécuté via des microservices asynchrones FastAPI et Redis, et appuyé par des modèles de langage haute performance Groq ainsi que la recherche web en temps réel Tavily AI.

ARCHITECTURE DU SYSTÈME
Le projet repose sur une orchestration par graphes d'états où plusieurs agents spécialisés collaborent pour produire des synthèses détaillées. Le Planner Agent analyse la question initiale et la découpe en sous-questions optimisées. Le Researcher Agent interroge l'API Tavily pour collecter des sources web pertinentes et filtrer l'information. Le Writer Agent syntétise les résultats et rédige un rapport structuré au format Markdown.

TECH STACK ET COMPOSANTS
L'API repose sur le framework FastAPI pour assurer l'exécution asynchrone et le streaming Server-Sent Events. L'orchestration des agents est gérée par LangGraph et LangChain. La génération de texte exploite l'API Groq Cloud avec les modèles Qwen 3.8 27B et GPT OSS 20B. La collecte d'informations s'appuie sur Tavily AI. La gestion d'état et le stockage de session sont confiés à Redis exécuté dans un conteneur Docker, tandis que la validation des données est assurée par Pydantic v2.

ENDPOINTS API DISPONIBLES
L'endpoint POST /research initie une nouvelle recherche en arrière-plan et retourne un identifiant unique de suivi. L'endpoint GET /research/{run_id} récupère le statut d'exécution (en cours, terminé ou échoué) ainsi que le rapport final. L'endpoint GET /research/{run_id}/stream fournit un flux SSE pour suivre la progression des agents en temps réel. L'endpoint GET /research/{run_id}/trace permet d'inspecter les étapes du graphe d'agents. Enfin, l'endpoint GET /health vérifie l'état de santé de l'API et des services tiers.

ACQUIS TECHNIQUES DU PROJET
Ce projet démontre la maîtrise d'une architecture multi-agents basée sur des graphes d'état décisionnels. Il illustre la mise en œuvre de la programmation asynchrone avec FastAPI pour traiter des tâches lourdes en arrière-plan sans bloquer le serveur. Il couvre également la transmission d'événements en temps réel au client via streaming ainsi que la persistance d'état dans Redis pour sécuriser le cycle de vie des exécutions.
