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

# Le site "default" Nginx bind le port 80, déjà occupé par le serveur driveby
# (autre projet). Il faut le désactiver pour que Nginx démarre (TechConnect = 8083).
echo "→ Désactivation du site Nginx par défaut (port 80 / driveby)"
sudo rm -f "/etc/nginx/sites-enabled/default"
# Le site driveby nginx est lui aussi inutilisé (driveby tourne hors Nginx) :
sudo rm -f /etc/nginx/sites-enabled/driveby

echo "→ Démarrage de Nginx (si ce n'est pas déjà fait)"
if ! systemctl is-active --quiet nginx; then
  sudo systemctl enable --now nginx
fi

echo "→ Vérification de la syntaxe"
sudo nginx -t

echo "→ Rechargement de Nginx"
sudo systemctl reload nginx

echo "✅ Nginx actif sur http://127.0.0.1:8083 (reverse proxy vers gunicorn 8000)"
echo "   Le tunnel ngrok pointe déjà sur 8083. Déploiement Nginx terminé."