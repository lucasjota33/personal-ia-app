# Halter AI

Aplicativo migrado de Streamlit para FastAPI + frontend estático.

## Estrutura

- `/api` - backend FastAPI
- `/public` - frontend estático (HTML, CSS, JS)
- `vercel.json` - configuração de deploy para Vercel
- `render.yaml` - configuração de deploy para Render
- `.env.sample` - exemplo de variáveis de ambiente

## Variáveis de ambiente

Defina as variáveis abaixo no ambiente de produção ou em um arquivo `.env` local.

- `FIREBASE_PROJECT_ID`
- `FIREBASE_API_KEY`
- `GEMINI_API_KEY`
- `CORS_ALLOW_ORIGINS` (opcional, padrão `[
"*"]`)

## Como executar localmente

1. Crie um ambiente virtual Python:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Copie `.env.sample` para `.env` e preencha os valores.
4. Inicie a API:
   ```bash
   uvicorn api.main:app --reload
   ```
5. Abra a pasta `public` com um servidor estático e acesse `http://localhost:8000`.
   Por exemplo:
   ```bash
   cd public
   python -m http.server 8000
   ```

## Deploy

### Vercel

- O backend é publicado em `/api`.
- O frontend estático é publicado a partir da pasta `public`.
- Certifique-se de inserir as variáveis de ambiente no painel do Vercel.

### Render

- `render.yaml` define um serviço `web` para o backend e um serviço `static_site` para o frontend.
- Configure as mesmas variáveis de ambiente no painel do Render.

## Endpoints principais

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/perfis`
- `POST /api/perfis`
- `GET /api/perfil/{nome}`
- `POST /api/chat/{perfil}`
- `GET /api/download-pdf/{perfil}`
- `DELETE /api/perfil/{nome}`
