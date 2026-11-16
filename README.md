# Bot de alertas

Comandos: /ban (banea del canal público + alerta), /mandar, /sapo, /pagado.

## Variables de entorno
- TELEGRAM_ALERTAS_TOKEN (obligatoria en producción)

## Railway
1. New Project → Deploy from GitHub repo.
2. Variables → TELEGRAM_ALERTAS_TOKEN = <token>.
3. Deploy. Es un worker: no necesita puerto ni dominio.

## Requisitos en Telegram
- BotFather → Bot Settings → Business Mode: ON
- Bot admin en el canal público con permiso de banear
- Solo un bot business conectado por cuenta