# Les Sentiers du rythme — version web de démonstration (prototype V0.3)

Application expérimentale d’exploration de la structure et des respirations des textes. **Du lustre, pas du lissage !**

## Déploiement sur Streamlit Community Cloud
1. Créer un dépôt GitHub, et y déposer les fichiers de ce dossier **à la racine** (`app.py`, `engine.py`, `sequence.py`, `requirements.txt`, `exemple_demo.txt`, `.streamlit/config.toml`).
2. Ne jamais ajouter de manuscrits personnels ou de secrets au dépôt.
3. Ouvrir https://share.streamlit.io, se connecter avec GitHub, choisir le dépôt et `app.py` comme point d’entrée.
4. Déployer et tester l’URL publique avec le texte de démonstration.
5. Avant d’inviter des auteurs à importer des textes inédits, définir une politique de confidentialité et évaluer les garanties de l’hébergeur.

## Lancer localement
`python -m pip install -r requirements.txt` puis `python -m streamlit run app.py`

## Confidentialité et limites
- L’import ODT en version web implique un transfert du fichier au serveur. Aucune promesse de traitement exclusivement local.
- Le code ne stocke pas volontairement les fichiers importés dans une base ni ne les envoie à une API tierce. Streamlit et l’hébergeur peuvent néanmoins traiter ou conserver temporairement certaines données techniques.
- Limite d’import configurée à 10 Mo. Le moteur conserve les blocs du texte dans la session pour l’analyse.
- Les exports JSON contiennent du texte source : les utilisateurs doivent les traiter comme des documents personnels.
- Les styles et espacements exacts du document ODT ne sont pas encore intégralement conservés.
- Cette version reste V0.3 ; la segmentation scènes (`❦`) / POV (prénoms en majuscules) est prévue pour V0.4, **pas encore implémentée**.

## Tests
`python -m pytest -q` (installer `pytest` séparément pour le développement).
