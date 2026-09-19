#!/usr/bin/env bash
# Déploiement de la config Nginx TechConnect Bénin (port 8080).
# À lancer UNE FOIS (sudo demandera le mot de passe) :
#   bash deploy/setup_nginx.sh
set -euo pipefail

PROJ="$HOME/Documents/TechConnect_Benin"
SITE=techconnect

echo "→ Copie de la config Nginx"
sudo cp "$PROJ/deploy/techconnect_nginx.conf" "/etc/nginx/sites-available/$SITE"
sudo ln -sf "/etc/nginx/sites-available/$SITE" "/etc/nginx/sites-enabled/$SITE"

echo "→ Démarrage de Nginx (si ce n'est pas déjà fait)"
if ! systemctl is-active --quiet nginx; then
  sudo systemctl enable --now nginx
fi

echo "→ Vérification de la syntaxe"
sudo nginx -t

echo "→ Rechargement de Nginx"
sudo systemctl reload nginx

echo "✅ Nginx actif sur http://127.0.0.1:8080 (reverse proxy vers gunicorn 8000)"
echo "   Étape suivante : rediriger le tunnel ngrok vers 8080 (je le fais pour toi)."