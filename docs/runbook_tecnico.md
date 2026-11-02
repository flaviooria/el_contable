<!-- docs-map: Runbook del despliegue continuo a VPS: credenciales, pasos por entorno y diagnóstico de fallos. -->

# Runbook técnico: despliegue de `el_contable`

Despliegue continuo de la API a un VPS: GitHub Actions construye la imagen, la
publica en GHCR y la despliega por SSH.

Este documento cubre los tres entornos (**PC local**, **GitHub**, **VPS**) y
funciona tanto con repo **público** como **privado**. Donde difieren, se indica
explícitamente.

---

## 1. Arquitectura y flujo de autenticación

El despliegue implica **tres comunicaciones distintas**, cada una con su propia
credencial. Confundirlas es el error más común al montar esto.

```
┌──────────────────────────┐
│  GitHub Actions (runner) │
└────────────┬─────────────┘
             │
             │ ① SSH  runner ──► VPS
             │    credencial: VPS_DEPLOY_KEY
             │    + VPS_KNOWN_HOSTS
             ▼
┌──────────────────────────┐
│  VPS  (usuario `deploy`) │
│   /opt/apps/el_contable  │
└────────────┬─────────────┘
             │
             │ ② SSH  VPS ──► GitHub   (git pull del código)
             │    credencial: deploy key  ← solo hace falta si el repo es privado
             ▼
┌──────────────────────────┐
│        GitHub (repo)     │
└──────────────────────────┘

┌──────────────────────────┐
│  VPS  (usuario `deploy`) │
└────────────┬─────────────┘
             │
             │ ③ HTTPS  VPS ──► GHCR   (docker pull de la imagen)
             │    credencial: VPS_GHCR_TOKEN (PAT) + VPS_GHCR_USERNAME
             ▼
┌──────────────────────────┐
│           GHCR           │
└──────────────────────────┘
```

### Tabla de credenciales

| # | Credencial | De → a | Para qué | Dónde vive | ¿Requerida con repo privado? |
|---|-----------|--------|----------|-------------|------------------------------|
| ① | `VPS_DEPLOY_KEY` | Runner → VPS | Ejecutar el deploy | Secret de GitHub | Sí |
| ① | `VPS_KNOWN_HOSTS` | Runner → VPS | Verificar identidad del VPS (anti-MITM) | Secret de GitHub | Sí |
| ② | Deploy key | VPS → GitHub | `git pull` del código | `~/.ssh/` del VPS + GitHub | **Sí** |
| ③ | `VPS_GHCR_TOKEN` | VPS → GHCR | `docker pull` de la imagen | Secret de GitHub | Sí (si el paquete es privado) |
| ③ | `VPS_GHCR_USERNAME` | — | Usuario del PAT | Secret de GitHub | Sí (si el paquete es privado) |

**Punto clave:** ① y ② son claves distintas y en direcciones opuestas.
`VPS_DEPLOY_KEY` es tu clave personal del PC, cuya parte pública está en
`authorized_keys` del VPS. La deploy key ② es una clave nueva, generada **en el
VPS**, cuya parte pública se registra en GitHub.

**El PAT nunca sirve para `git pull`** y **una deploy key nunca sirve para
`docker pull`**: son protocolos distintos (SSH vs. HTTPS) sobre servicios
distintos (Git vs. GHCR).

---

## 2. Estado actual verificado (2026-11-02)

Verificado por inspección del VPS y del PC local.

> ### ⚠️ Existen DOS servidores distintos
>
> | Servidor | IP | Uso | Accesible desde GitHub Actions |
> |----------|----|-----|-------------------------------|
> | **VPS de producción** | `62.171.145.58` | Traefik + Postgres + API | ✅ Sí — puerto 22 abierto |
> | **Lab local (Vagrant)** | `192.168.56.10` | `vps-lab`, pruebas en LAN | ❌ No — IP privada detrás de NAT |
>
> El secret `VPS_HOST` **debe** ser `62.171.145.58`. Con la IP del lab local el
> runner falla con `Connection timed out` (ver sección 9).
>
> El lab local (`192.168.56.10`) sí tiene el setup completo de deploy key y
> repo inicializado, pero **no** es el destino del despliegue.

### PC local

| Elemento | Estado |
|----------|--------|
| Alias SSH `deploy-vps` | ⚠️ Apunta al lab (`192.168.56.10`), **no** al VPS de producción |
| Alias SSH `admin-vps` | ⚠️ Apunta al lab (`192.168.56.10`), **no** al VPS de producción |
| Acceso al VPS de producción | ✅ `ssh -i ~/.ssh/vps_deploy deploy@62.171.145.58` |
| Acceso admin al VPS de producción | ✅ `ssh -i ~/.ssh/vps_admin admin@62.171.145.58` (sudo pide password) |
| `ssh git@github.com` | ✅ Autentica como `flaviooria` |
| Remote `origin` | `git@github.com:flaviooria/el_contable.git` |

### VPS de producción (`62.171.145.58`)

| Elemento | Estado |
|----------|--------|
| Usuario `deploy` | ✅ uid=1002, grupos: `deploy, users, docker` |
| Permisos Docker | ✅ **usuario `deploy` está en el grupo `docker`** |
| Docker Engine | ✅ v29.9.1 |
| Docker Compose | ✅ v5.6.0 (soporta `--env-file` múltiple) |
| Red `proxy` externa | ✅ Existe (la usa Traefik v3.7) |
| Contenedores activos | ✅ `traefik`, `socket-proxy` |
| Repo en `/opt/apps/el_contable` | ✅ Clonado, commit `5bce56f`, working tree limpio |
| **Propietario del repo** | ❌ **Es de `root`** → Git da `dubious ownership` y `deploy` no puede escribir en `.git` |
| `known_hosts` de github.com | ✅ Configurado (ssh-rsa + ssh-ed25519) |
| `.env.prod` | ✅ Existe con credenciales reales |
| `movements_files/` | ❌ No existe |
| `safe.directory` de git | ✅ Configurado |
| Clave de deploy para GitHub | ❌ No existe en este servidor |

### Lab local (`192.168.56.10`)

| Elemento | Estado |
|----------|--------|
| Usuario `deploy` | ✅ uid=1002, grupos: `deploy, users, docker` |
| Docker Engine | ✅ v29.9.2 |
| Docker Compose | ✅ v5.6.1 |
| Red `proxy` externa | ✅ Existe |
| Clave de deploy para GitHub | ✅ `~/.ssh/ghcr_deploykey` (600) |
| `~/.ssh/config` | ✅ `IdentityFile` + `IdentitiesOnly yes` |
| `known_hosts` de github.com | ✅ ssh-rsa + ssh-ed25519 |
| Repo git inicializado | ✅ `git init` + remoto `origin` |
| Excludes de `.env*` | ✅ en `.git/info/exclude` |
| `movements_files/` | ✅ Creado |
| Clave registrada en GitHub | ❌ Pendiente (sección 5.2) |
| Working tree del repo | ❌ Sin contenido (falta `git fetch`) |
| `.env.prod` | ❌ No existe (sección 3.5) |

### Pendiente en GitHub

| Elemento | Estado |
|----------|--------|
| Deploy key del repo | ❌ **Pendiente** (sección 5.2) |
| Secret `VPS_DEPLOY_KEY` | ⚠️ Por confirmar (la clave `vps_deploy` del PC existe) |
| Secret `VPS_KNOWN_HOSTS` | ⚠️ Por confirmar (comando en 6.3) |
| Secret `VPS_HOST` | ⚠️ Por confirmar (`192.168.56.10`) |
| Secret `VPS_USER` | ⚠️ Por confirmar (`deploy`) |
| Secret `VPS_GHCR_USERNAME` | ⚠️ Por confirmar (debe ser `flaviooria`) |
| Secret `VPS_GHCR_TOKEN` | ⚠️ Por crear (PAT clásico, scope `read:packages`) |
| Variable `VPS_DEPLOY_PATH` | Opcional, default `/opt/apps/el_contable` |
| Visibilidad del paquete GHCR | ⚠️ Revisar tras el primer push |

---

## 2.1 Procedimiento de puesta en marcha (checklist ejecutable)

Estado de avance real, verificado por ejecución de cada comando.

```
[✅] VPS: grupo docker, Docker, Compose v5, red proxy
[✅] VPS: deploy key generada + ssh config + known_hosts
[✅] VPS: repo inicializado + remoto origin + excludes
[✅] VPS: movimientos_files/ creado
[ ] GITHUB: registrar deploy key (5.2)              ← TÚ
[ ] VPS: git fetch + reset --hard (3.4/5.5)         ← depende del anterior
[ ] VPS: crear .env.prod (3.5)                      ← TÚ
[ ] GITHUB: crear secrets (6.1-6.4)                 ← TÚ
[ ] GITHUB: ejecutar workflow (8.2)
[ ] GITHUB: paquete GHCR → Private (7.1)            ← TÚ
```

### Comandos de verificación

```bash
# ¿La deploy key funciona? (debe responder "Hi <owner>/el_contable!")
ssh deploy-vps 'ssh -T git@github.com 2>&1 | head -2'

# ¿El repo está sincronizado?
ssh deploy-vps 'cd /opt/apps/el_contable && git log --oneline -1 && git status --short'

# ¿Existe el .env.prod?
ssh deploy-vps 'test -f /opt/apps/el_contable/.env.prod && echo OK || echo FALTA'

# ¿Está el usuario en el grupo docker?
ssh deploy-vps 'groups | grep -o docker || echo "SIN PERMISOS DOCKER"'

# ¿El compose resuelve la imagen?
ssh deploy-vps 'cd /opt/apps/el_contable && cp .env.prod .env.prod.test && \
  IMAGE_TAG=sha-test docker compose -f compose.prod.yml --env-file .env.prod.test config && \
  rm .env.prod.test'
```

---

## 3. Preparación del VPS

> Ejecutar como `deploy` salvo indicación contraria.
> Usa `ssh deploy-vps` desde el PC local para entrar.

### 3.1 Crear el directorio de despliegue

**Ya ejecutado.**

```bash
ssh deploy-vps
mkdir -p /opt/apps/el_contable
cd /opt/apps/el_contable
```

`/opt/apps/` ya existe y pertenece a `deploy`.

### 3.2 Crear el directorio de ficheros subidos

**Ya ejecutado.**

```bash
mkdir -p /opt/apps/el_contable/movements_files
```

El servicio `api` monta este directorio. Si no existe, Docker lo crearía como
root y los ficheros quedarían fuera del control del usuario `deploy`.

### 3.3 Configurar el repositorio remoto

**Ya ejecutado** (`git init` + `git remote add` + excludes).

> Si aún no has clonado el repo (sección 3.4), el flujo es:
> `git init` → `git remote add` → `git fetch` → `git reset --hard origin/main`.
> Así el VPS tiene el historial completo y el `git pull --ff-only` del workflow
> no fallará por un repo sin commits.

```bash
cd /opt/apps/el_contable
git init
git remote add origin git@github.com:flaviooria/el_contable.git
git fetch origin main
git reset --hard origin/main
git checkout -B main
```

Para que el `git pull` del workflow no falle, el repo debe estar en `main` y sin
cambios sin commitear. Los ficheros de entorno se ignoran **por repo** (no por
`.gitignore` versionado) para no ensuciar commits:

```bash
printf '.env\n.env.prod\n.env.deploy\n' >> /opt/apps/el_contable/.git/info/exclude
```

### 3.4 Poblar el repositorio con el código

**Pendiente**: requiere que la deploy key esté registrada (5.2) o que el repo
sea público.

```bash
ssh deploy-vps 'cd /opt/apps/el_contable && \
  git fetch origin main && \
  git reset --hard origin/main && \
  git checkout -B main && \
  git log --oneline -1'
```

> Se usa `fetch` + `reset --hard` en lugar de `git clone` porque el repo ya está
> inicializado, y porque deja el working tree exactamente en el estado que
> espera `git pull --ff-only origin main` (que es lo que ejecuta el workflow).
>
> Equivalente si prefieres empezar de cero:
>
> ```bash
> cd /opt/apps
> rm -rf el_contable
> git clone git@github.com:flaviooria/el_contable.git el_contable
> cd el_contable
> ```
>
> Con repo **privado**, ambas formas **fallan** hasta que configures la deploy
> key (sección 5).
>
> Alternativa si prefieres que el workflow NO dependa de un clone de git en el
> VPS: el workflow podría enviar el `compose.prod.yml` por `scp` en lugar de
> hacer `git pull`. El diseño actual asume clone de git.

> Con repo **privado** este `git clone` **falla** hasta que configures la
> deploy key (sección 5). En ese caso, monta primero la deploy key (5.1–5.4) y
> luego repite este `git clone`.
>
> Alternativa si prefieres que el workflow NO dependa de un clone de git en el
> VPS: el workflow podría enviar el `compose.prod.yml` por `scp` en lugar de
> hacer `git pull`. El diseño actual asume clone de git.

### 3.5 Crear el `.env.prod`

Este fichero contiene las credenciales de Postgres y el dominio. **No lo
versiona**; el workflow solo lo lee.

```bash
cat > /opt/apps/el_contable/.env.prod <<'EOF'
POSTGRES_USER=el_contable
POSTGRES_PASSWORD=<CONTRASEÑA_FUERTE>
POSTGRES_DB=el_contable

DOMAIN=tudominio.com
EOF

chmod 600 /opt/apps/el_contable/.env.prod
```

> El `DOMAIN` lo usan las etiquetas de Traefik del servicio `api`
> (`Host(\`api.${DOMAIN}\`)`). Debe coincidir con el dominio real para el que
> Traefik emite el certificado TLS.
>
> Este fichero **no lo crea ni lo actualiza el workflow**: el workflow solo lo
> lee (`--env-file .env.prod`). Si cambias las credenciales de Postgres, hay
> que editarlo a mano en el VPS.

### 3.6 Permisos

```bash
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.env.prod
mkdir -p /home/deploy/.ssh && chmod 700 /home/deploy/.ssh
```

### 3.7 Corregir el ownership del repo (requiere sudo)

> ⏳ **PASO PENDIENTE en el VPS de producción.** El repo se clonó como `root`,
> pero el workflow se conecta como `deploy`. Eso provoca dos fallos:
> `detected dubious ownership in repository` y
> `error: cannot open '.git/FETCH_HEAD': Permission denied`.

El usuario `deploy` **no** puede hacer `chown` sobre ficheros de `root`. El
cambio requiere `sudo`, es decir, un usuario con privilegios administrativos:

```bash
ssh admin@62.171.145.58
sudo chown -R deploy:deploy /opt/apps/el_contable
sudo chmod -R u+rwX /opt/apps/el_contable
sudo mkdir -p /opt/apps/el_contable/movements_files
sudo chown deploy:deploy /opt/apps/el_contable/movements_files
```

Registrar el directorio como seguro para git (como usuario `deploy`):

```bash
ssh deploy@62.171.145.58
git config --global --add safe.directory /opt/apps/el_contable
```

Verificar:

```bash
ssh deploy@62.171.145.58 'cd /opt/apps/el_contable && git status && git pull --ff-only origin main'
```

> **Por qué no basta con `safe.directory`:** esa opción solo silencia el aviso de
> Git; no cambia los permisos del sistema de ficheros. Sin el `chown`, el
> `git pull` sigue fallando al no poder escribir en `.git/FETCH_HEAD`.
>
> **Por qué no conviene re-clonar:** `rm -rf` sobre ficheros de `root` también
> requiere `sudo`. El `chown` es menos destructivo: no toca el contenido del
> repo ni el `.env.prod`.
>
> **Regla general:** el directorio de despliegue debe ser propiedad del usuario
> que ejecuta el deploy, desde el primer `git clone`. Si se clona como `root`,
> el ownership hay que corregirlo una vez.

---

## 4. Repo PÚBLICO (flujo mínimo)

Con repo público, el `git pull` del VPS funciona **sin credencial**: el servidor
GitHub acepta lecturas anónimas de repos públicos. No hace falta deploy key.

### 4.1 Verificar que el pull funciona

```bash
ssh deploy-vps 'ssh -T git@github.com 2>&1 | head -2'
```

> Estado actual: devuelve `Permission denied (publickey)` porque la deploy key
> **aún no está registrada en GitHub** (sección 5.2). Es lo esperado.

Hay que distinguir dos errores distintos:

| Error | Causa | Solución |
|-------|-------|----------|
| `Host key verification failed` | Falta `known_hosts` de github.com | `ssh-keyscan github.com >> ~/.ssh/known_hosts` |
| `Permission denied (publickey)` | La clave no está registrada en GitHub | Sección 5.2 |

El `known_hosts` **ya está configurado** en este VPS:

```bash
ssh deploy-vps 'cut -d" " -f1,2 ~/.ssh/known_hosts'
# github.com ssh-rsa
# github.com ssh-ed25519
```

### 4.2 Verificar el pull

```bash
ssh deploy-vps 'cd /opt/apps/el_contable && git fetch origin main && git log --oneline -1 origin/main'
```

### 4.3 Nota sobre la lectura anónima

El `git pull` con repo público usa la URL `git@github.com:...` pero **no
presenta ninguna clave**. GitHub lo permite para repos públicos. Cuando el repo
pase a privado, este mismo paso empezará a fallar con `Permission denied
(publickey)`.

---

## 5. Repo PRIVADO (requiere deploy key)

Para repos privados, el VPS debe autenticarse ante GitHub. La forma con menor
privilegio es una **deploy key de solo lectura**, asociada al repositorio.

### 5.1 Generar la clave EN EL VPS

> La clave privada **nunca debe salir del VPS**. Solo se copia la `.pub`.

**Ya ejecutado en este VPS.** La clave existe en `~/.ssh/ghcr_deploykey`:

```bash
ssh deploy-vps 'cat ~/.ssh/ghcr_deploykey.pub'
```

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIENlevjkRYFCWFcV2lTK+DFi35X229Md5Bq3AKXttV98 el-contable-vps-deploykey
```

Fingerprint: `SHA256:datTLxoDzDGCrhgT8Or7CTe4CuSkTzqESKkfm5U3Wq4`

Para regenerarla desde cero (por ejemplo, si se sospecha exposición):

```bash
ssh deploy-vps
ssh-keygen -t ed25519 -C "el-contable-vps-deploykey" -f ~/.ssh/ghcr_deploykey -N ""
cat ~/.ssh/ghcr_deploykey.pub
```

> Regenerarla **invalida** la que estuviera registrada en GitHub: habría que
> actualizar la deploy key allí también.

### 5.2 Registrar la clave pública en GitHub

> ⏳ **PASO PENDIENTE.** Hasta que se complete, el `git pull` del VPS no puede
> autenticarse ante GitHub. Con repo público funciona por lectura anónima, pero
> la deploy key no estaría ejercitada.

1. GitHub → repositorio `flaviooria/el_contable`
2. **Settings** → **Deploy keys** → **Add deploy key**
3. *Title*: `vps-deploy`
4. *Key*: pega el contenido de `~/.ssh/ghcr_deploykey.pub`
5. **NO** marques "Allow write access"

### 5.3 Configurar el uso de la clave en el VPS

**Ya ejecutado.** `~/.ssh/config` contiene:

```bash
cat > /home/deploy/.ssh/config <<'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/ghcr_deploykey
  IdentitiesOnly yes
EOF

chmod 600 /home/deploy/.ssh/config
```

`IdentitiesOnly yes` evita que SSH ofrezca todas las claves disponibles (puede
provocar `too many authentication failures`).

### 5.4 Verificar

```bash
ssh deploy-vps 'ssh -T git@github.com 2>&1 | head -2'
```

Salida esperada: `Hi flaviooria/el_contable! You've successfully authenticated...`

> Con una deploy key, GitHub identifica al **repo**, no a la persona. Por eso el
> mensaje dice `Hi flaviooria/el_contable!` en lugar de `Hi flaviooria!` (que
> es lo que devuelve tu clave personal).

Si sigue apareciendo `Permission denied (publickey)`, revisa que:
- la clave pública en GitHub sea **exactamente** la del VPS,
- `~/.ssh/config` tenga la ruta correcta,
- los permisos sean `600` en la clave y `600` en el config.

### 5.5 Poblar el repo y verificar el pull

```bash
ssh deploy-vps 'cd /opt/apps/el_contable && \
  git fetch origin main && \
  git reset --hard origin/main && \
  git checkout -B main && \
  git log --oneline -1 && \
  git status --short'
```

Salida esperada: el hash del último commit de `main` y **cero líneas** en
`git status` (working tree limpio, requisito para que el `git pull --ff-only`
del workflow no falle).

### 5.6 ¿Y si ya tengo mi clave personal en el VPS?

Si copiaste tu clave personal (`~/.ssh/vps_deploy` del PC) al VPS, GitHub la
aceptará porque es una clave de tu cuenta. **Funciona, pero no es recomendable**:
esa clave da acceso a *todos* tus repositorios privados. Si el VPS se compromete,
el atacante entra en todo tu GitHub. La deploy key limita el daño a un repo.

### 5.7 Volver de privado a público

Puedes eliminar la deploy key (GitHub → Settings → Deploy keys → Delete). El
`git pull` seguirá funcionando, ahora en modo anónimo.

---

## 6. Credenciales de GitHub Actions (Settings del repo)

### 6.1 Secrets

Ruta: **Settings** → **Secrets and variables** → **Actions** → **Secrets**.

| Secret | Valor | Cómo obtenerlo |
|--------|-------|----------------|
| `VPS_HOST` | `62.171.145.58` | **IP pública** del VPS de producción |
| `VPS_USER` | `deploy` | Usuario SSH del VPS |
| `VPS_DEPLOY_KEY` | Clave privada `~/.ssh/vps_deploy` | Ver 6.2 |
| `VPS_KNOWN_HOSTS` | Host keys del VPS | Ver 6.3 |
| `VPS_GHCR_USERNAME` | `flaviooria` | Dueño del PAT |
| `VPS_GHCR_TOKEN` | PAT clásico `read:packages` | Ver 6.4 |

> ⚠️ `VPS_HOST` **no** puede ser una IP privada (`192.168.x.x`, `10.x.x.x`).
> El runner de GitHub Actions está en Internet y no tiene ruta hacia tu LAN:
> el job falla con `ssh: connect to host ... port 22: Connection timed out`.

### 6.2 `VPS_DEPLOY_KEY`

Es tu clave **`vps_deploy`** del PC local (la que ya está en
`authorized_keys` del VPS). Copia el **contenido íntegro** del fichero, con las
líneas `-----BEGIN OPENSSH PRIVATE KEY-----` y `-----END OPENSSH PRIVATE KEY-----`
y el salto de línea final:

```bash
cat ~/.ssh/vps_deploy
```

> Error frecuente: si el secret pierde el salto de línea final o una línea
> intermedia, el `printf` del workflow genera una clave inválida y el SSH falla
> con `invalid format` o `bad permissions`.

### 6.3 `VPS_KNOWN_HOSTS`

```bash
ssh-keyscan -p 22 62.171.145.58 > /tmp/vps_known_hosts 2>/dev/null
cat /tmp/vps_known_hosts
```

Verifica el fingerprint contra el que muestra el VPS para evitar MITM:

```bash
ssh admin-vps 'ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub'
```

Pega el contenido de `/tmp/vps_known_hosts` en el secret.

> ¿Por qué es necesario? Sin `known_hosts`, un atacante que controle el DNS
> podría hacer MITM y capturar tu clave privada.

### 6.4 `VPS_GHCR_TOKEN`

**Personal Access Token clásico** (los fine-grained no gestionan paquetes de
forma fiable para `docker login`):

1. GitHub → avatar → **Settings** → **Developer settings** → **Personal access
   tokens** → **Tokens (classic)** → **Generate new token (classic)**
2. **Scope**: marca **`read:packages`** (único necesario)
3. **Expiration**: 60 días (pon un recordatorio para renovarlo)
4. Copia el token (solo se muestra una vez)

> Si tu organización tiene SAML SSO activo, añade el scope
> `sso:authorization` y autoriza la organización para ese token. Si no,
> `docker login` fallará con `403 denied` aunque los scopes sean correctos.

> `write:packages` **no** es necesario: el workflow publica con
> `GITHUB_TOKEN`, no con este PAT.

> **Alcance**: `read:packages` da acceso a *todos* los paquetes privados de tu
> cuenta, no solo al de este repo. Para una app personal es un riesgo bajo. La
> alternativa es hacer el paquete GHCR público y eliminar este secret.

### 6.5 Variables (opcional)

Ruta: **Settings** → **Secrets and variables** → **Actions** → **Variables**.

| Variable | Default | Descripción |
|----------|---------|-------------|
| `VPS_DEPLOY_PATH` | `/opt/apps/el_contable` | Ruta del repo en el VPS |

---

## 7. Visibilidad del paquete GHCR

**La visibilidad del paquete es independiente de la del repo.** GHCR no tiene
"privado" como opción al publicar: el paquete **hereda** la visibilidad del repo
en el primer push y se cambia después a mano.

| Visibilidad repo | Visibilidad inicial del paquete | Acción |
|------------------|-------------------------------|--------|
| Público | Público | Cambiar a **Private** a mano (paso 7.1) |
| Privado | Privado | Nada |

### 7.1 Cambiar el paquete a privado

Tras el primer build (el paquete debe existir):

1. GitHub → perfil → **Packages** → `el_contable`
2. **Package settings** → **Change visibility** → **Private**

> Si el repo es **público** y dejas el paquete **público**, puedes eliminar
> `VPS_GHCR_TOKEN` y el paso `docker login` del workflow. La imagen es de una app
> personal y el código ya es visible en el repo público.

### 7.2 Verificar la visibilidad desde el PC

```bash
# Sin token: funciona solo si el paquete es público
docker pull ghcr.io/flaviooria/el_contable:latest

# Con token: funciona con paquete privado
echo "$VPS_GHCR_TOKEN" | docker login ghcr.io -u flaviooria --password-stdin
docker pull ghcr.io/flaviooria/el_contable:latest
```

---

## 8. Primer despliegue

### 8.1 Verificación previa

Todos estos comandos deben pasar **antes** de lanzar el workflow:

```bash
# 1. La deploy key funciona (debe decir "Hi flaviooria/el_contable!")
ssh deploy-vps 'ssh -T git@github.com 2>&1 | head -2'

# 2. El VPS puede hacer pull y el working tree está limpio
ssh deploy-vps 'cd /opt/apps/el_contable && git fetch origin main && git log --oneline -1 && git status --short'

# 3. Existe el .env.prod
ssh deploy-vps 'test -f /opt/apps/el_contable/.env.prod && echo OK || echo FALTA'

# 4. El usuario tiene permisos de Docker
ssh deploy-vps 'groups | grep -o docker || echo "SIN PERMISOS DOCKER"'

# 5. El compose resuelve la imagen correctamente
ssh deploy-vps 'cd /opt/apps/el_contable && cp .env.prod .env.prod.test && \
  IMAGE_TAG=sha-test docker compose -f compose.prod.yml --env-file .env.prod.test config && \
  rm .env.prod.test'

# 6. Los secrets existen en GitHub
# (Settings → Secrets and variables → Actions)
```

> El paso 5 usa `.env.prod` y **no** `.env.example` a propósito: el servicio `db`
> declara `env_file: .env.prod`, y Compose exige que ese fichero exista para
> poder resolver la configuración.

### 8.2 Ejecutar el workflow

1. GitHub → repo → pestaña **Actions**
2. Selecciona el workflow **deploy**
3. **Run workflow** → *Branch*: `main` → *image_tag*: (vacío = `sha-<sha actual>`)
4. **Run workflow**

### 8.3 Secuencia que ejecuta el job `deploy`

Todo ocurre dentro de una única conexión SSH al VPS:

```
set -e
cd /opt/apps/el_contable
git pull --ff-only origin main                                   ← ②
printf '%s' '$TOKEN' | docker login ghcr.io -u '$USER' --password-stdin  ← ③
printf 'IMAGE_TAG=%s\n' 'sha-abc...' > .env.deploy
docker compose ... config                                        ← validación
docker compose ... pull                                          ← ③ descarga imagen
docker compose ... up -d db                                      ← Postgres
docker compose ... run --rm api alembic upgrade head             ← migraciones
docker compose ... up -d --remove-orphans                        ← API
```

### 8.4 Verificar el resultado

```bash
# Estado de los contenedores
ssh deploy-vps 'docker compose -f /opt/apps/el_contable/compose.prod.yml \
  --env-file /opt/apps/el_contable/.env.prod \
  --env-file /opt/apps/el_contable/.env.deploy ps'

# Logs de la API
ssh deploy-vps 'docker logs -f el_contable_api'

# Health
curl -sS -o /dev/null -w '%{http_code}\n' https://api.tudominio.com/docs'
```

### 8.5 Rollback

```bash
ssh deploy-vps 'cd /opt/apps/el_contable && \
  printf "IMAGE_TAG=%s\n" "sha-<commit-anterior>" > .env.deploy && \
  docker compose -f compose.prod.yml --env-file .env.prod --env-file .env.deploy \
  up -d --remove-orphans'
```

O desde GitHub: **Actions** → *deploy* → **Run workflow** → `image_tag` =
`sha-<commit-anterior>`. El job `build` haría checkout de ese ref y reconstruiría
la imagen, por lo que el rollback es más lento pero reproducible.

---

## 9. Diagnóstico de fallos

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `ssh: connect to host ... port 22: Connection timed out` | `VPS_HOST` es una **IP privada** (LAN/Vagrant) y el runner no tiene ruta | Usar la IP pública: `62.171.145.58` (sección 2) |
| `detected dubious ownership in repository` | El repo es de `root` y el job corre como `deploy` | `chown -R deploy:deploy /opt/apps/el_contable` + `git config --global --add safe.directory <path>` |
| `error: cannot open '.git/FETCH_HEAD': Permission denied` | El usuario no puede escribir en `.git` (ownership de `root`) | Mismo `chown` que el caso anterior |
| `Permission denied (publickey)` en el `ssh` del runner | `VPS_DEPLOY_KEY` mal copiada (falta salto de línea) | Recopiar el secret desde `cat ~/.ssh/vps_deploy` |
| `Host key verification failed` en el VPS | Falta `known_hosts` de github.com | `ssh-keyscan github.com >> ~/.ssh/known_hosts` |
| `Permission denied (publickey)` en `git pull` | Repo privado sin deploy key | Sección 5 |
| `unauthorized` en `docker login` | PAT inválido, expirado o scope `read:packages` ausente | Regenerar el PAT |
| `403 denied` en `docker login` | SAML SSO activo sin `sso:authorization` | Añadir scope y autorizar la org |
| `denied: requested access to the resource is denied` en `docker pull` | Paquete privado sin sesión iniciada o PAT de otra cuenta | `docker login` con `VPS_GHCR_USERNAME` correcto |
| `permission denied while trying to connect to the Docker daemon` | Usuario `deploy` no está en el grupo `docker` | `sudo usermod -aG docker deploy` + reiniciar sesión |
| `Cannot connect to the Docker daemon` | Docker no arrancado | `sudo systemctl start docker` |
| `error pulling image ... manifest unknown` | El tag no existe en GHCR | Verificar tags publicados |
| `git pull` falla con `Your local changes would be overwritten` | Ficheros sin commitear en el VPS | `git status` y limpiar |
| `fatal: Need to specify how to reconcile divergent branches` | El repo del VPS diverge de GitHub | `git fetch && git reset --hard origin/main` (descarta cambios locales) |
| `network proxy declared as external, but could not be found` | La red externa de Traefik no existe | `docker network create proxy` (ya existe en este VPS) |
| `permission denied` al escribir en `movements_files` | Directorio con ownership equivocado | `chown deploy:deploy movements_files` |

---

## 10. Checklist de migración de repo público a privado

1. Monta la deploy key (**sección 5**) **mientras el repo sigue siendo público**.
2. Verifica que `ssh deploy-vps 'ssh -T git@github.com'` funciona.
3. Verifica el pull: `ssh deploy-vps 'cd /opt/apps/el_contable && git pull --ff-only origin main'`.
4. Ejecuta un deploy completo con el repo aún público (valida ③ y el compose).
5. Cambia el repo a **Private** en GitHub.
6. Ejecuta un deploy de nuevo para confirmar que ② sigue funcionando.

> Hazlo en ese orden. Si el repo pasa a privado antes de tener la deploy key,
> el `git pull` del workflow falla y el deploy se detiene — pero **el servicio
> que ya está corriendo no se ve afectado**, porque el deploy es idempotente y
> falla en la primera etapa, antes de tocar contenedores.

---

## 11. Mantenimiento

### Renovación del PAT

Cada 60 días:Settings → Developer settings → Personal access tokens → regenerar
o crear uno nuevo con `read:packages` → actualizar el secret `VPS_GHCR_TOKEN` en
el repo.

### Renovación de la deploy key del runner

1. Genera un par nuevo en el PC: `ssh-keygen -t ed25519 -f ~/.ssh/vps_deploy_new -N ""`
2. Añade la `.pub` al `authorized_keys` del VPS (mantén la antigua hasta verificar)
3. Actualiza el secret `VPS_DEPLOY_KEY`
4. Verifica con un workflow manual
5. Elimina la clave antigua del `authorized_keys` y borra el fichero local

### Limpieza en el VPS

```bash
# Imágenes sin usar
ssh deploy-vps 'docker image prune -f'

# Logs de Actions (si el disco se llena)
ssh deploy-vps 'du -sh /var/lib/docker/* | sort -h | tail'
```

---

## 12. Referencias

- Workflow: `.github/workflows/deploy.yml`
- Compose de producción: `compose.prod.yml`
- Variables de entorno: `.env.example` (plantilla), `.env.prod` (VPS, no versionado)
- Decisiones de arquitectura: `docs/decisions/`
- Especificaciones: `openspec/specs/`
