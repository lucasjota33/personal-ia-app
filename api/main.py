import io
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Optional
from .config import settings
from .auth import hash_password, verify_password, generate_token
from .firestore_utils import (
    get_user,
    save_user,
    find_user_by_email,
    find_user_by_token,
    delete_profile,
)
from .gemini_utils import call_gemini, extract_ai_text
from .pdf_generator import gerar_pdf
from .models import (
    AuthRequest,
    RegisterRequest,
    TokenResponse,
    PerfilCreateRequest,
    ChatRequest,
)

app = FastAPI(title="Halter AI API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root():
    return {"status": "ok", "message": "Halter AI API está rodando", "docs": "/docs"}


def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = parts[1]
    user = find_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


@app.post("/auth/register", response_model=TokenResponse)
def register(payload: RegisterRequest):
    existing = find_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    if get_user(payload.username):
        raise HTTPException(status_code=400, detail="Nome de utilizador já existe")

    token = generate_token()
    user_doc = {
        "email": payload.email,
        "senha": hash_password(payload.senha),
        "token": token,
        "perfis": {},
    }
    if not save_user(payload.username, user_doc):
        raise HTTPException(status_code=500, detail="Erro ao criar utilizador")
    return {"token": token}


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: AuthRequest):
    username = payload.login
    user = get_user(username)
    if not user:
        found = find_user_by_email(username)
        if found:
            username = found["username"]
            user = get_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    if not verify_password(payload.senha, user.get("senha", "")):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = generate_token()
    user["token"] = token
    if not save_user(username, user):
        raise HTTPException(status_code=500, detail="Erro ao atualizar token")
    return {"token": token}


@app.get("/perfis")
def list_perfis(current_user=Depends(get_current_user)):
    perfis = current_user.get("perfis") or {}
    return {"perfis": perfis}


@app.post("/perfis")
def create_perfil(request: PerfilCreateRequest, current_user=Depends(get_current_user)):
    username = current_user["username"]
    perfis = current_user.get("perfis") or {}
    if request.nome in perfis:
        raise HTTPException(status_code=400, detail="Perfil já existe")

    prompt = f"""
Atue como um Nutricionista Esportivo Clínico e Personal Trainer de extrema qualidade.
Crie um planejamento irretocável e personalizado para o(a) {request.nome}.
Idade: {request.idade} anos | Sexo: {request.sexo}
Peso: {request.peso}kg | Altura: {request.altura}cm | Nível: {request.nivel} | Objetivo: {request.objetivo}
Alergias/Restrições: {request.alergias or 'Nenhuma'}

# PLANEJAMENTO: {request.nome.upper()}

## 🧬 1. ANÁLISE METABÓLICA
Crie uma tabela em Markdown seguindo EXATAMENTE as colunas abaixo:
| Taxa Metabólica Basal (Mifflin-St Jeor)| Gasto Energético Total | Meta Calórica Alvo |

## 🥗 2. PLANO ALIMENTAR
Crie uma tabela em Markdown seguindo EXATAMENTE as colunas abaixo (Seja variado na criação do plano, não monte algo genérico e respeite as restrições alimentares mencionadas):
| Refeição(Almoço, janta, etc) | Alimento Principal | Macronutrientes | Substituição |

## ⚡ 3. PLANILHA DE TREINAMENTO
Defina uma divisão semanal inteligente com base no objetivo e sexo.
Para CADA DIA de treino, crie uma tabela em Markdown seguindo EXATAMENTE as colunas abaixo:
| Exercício | Séries | Repetições | Descanso |

## 💊 4. SUPLEMENTAÇÃO
| Suplemento | Dosagem Diária | Horário |

INSTRUÇÃO OBRIGATÓRIA PARA DASHBOARD:
No final absoluto da sua resposta, insira APENAS UM bloco de código json contendo as metas numéricas diárias, seguindo estritamente esta estrutura:
```json
{
    "calorias": 0,
    "proteinas_g": 0,
    "carboidratos_g": 0,
    "gorduras_g": 0,
    "tmb": 0,
    "gasto_total": 0,
    "agua_ml": 0,
    "passos": 0
}
```
Substitua os zeros pelos valores calculados em números inteiros (apenas números). Estime a água e passos diários.
"""

    response_data = call_gemini(prompt)
    content = extract_ai_text(response_data)
    if not content:
        raise HTTPException(status_code=500, detail="Falha ao gerar planejamento")

    current_user["perfis"] = perfis
    current_user["perfis"][request.nome] = {
        "dados": request.dict(),
        "mensagens": [{"role": "assistant", "content": content}],
    }
    if not save_user(username, current_user):
        raise HTTPException(status_code=500, detail="Erro ao salvar perfil")

    return current_user["perfis"][request.nome]


@app.get("/perfil/{nome}")
def get_perfil(nome: str, current_user=Depends(get_current_user)):
    perfis = current_user.get("perfis") or {}
    perfil = perfis.get(nome)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    return perfil


@app.post("/chat/{perfil}")
def chat_with_perfil(perfil: str, request: ChatRequest, current_user=Depends(get_current_user)):
    perfis = current_user.get("perfis") or {}
    perfil_data = perfis.get(perfil)
    if not perfil_data:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    mensagens = perfil_data.get("mensagens", [])
    plano_atual = ""
    for msg in reversed(mensagens):
        if msg.get("role") == "assistant" and "## 🧬" in msg.get("content", ""):
            plano_atual = msg["content"]
            break
    if not plano_atual and mensagens:
        plano_atual = mensagens[0].get("content", "")

    mensagens.append({"role": "user", "content": request.mensagem})
    prompt = f"""
Plano Atual do Perfil:
{plano_atual}

Mensagem do Usuário: {request.mensagem}

REGRA DE ATUALIZAÇÃO DO DASHBOARD:
Se o usuário pedir alteração na dieta, treino ou suplementos, REESCREVA o plano completo aplicando as mudanças. Mantenha a mesma estrutura de marcação e inclua o bloco ```json``` com os dados numéricos atualizados.
Se for apenas uma dúvida, responda de forma curta, sem reescrever o plano.
"""

    response_data = call_gemini(prompt, timeout=45)
    resposta = extract_ai_text(response_data)
    if not resposta:
        raise HTTPException(status_code=500, detail="Falha ao gerar resposta do chat")

    mensagens.append({"role": "assistant", "content": resposta})
    perfil_data["mensagens"] = mensagens
    current_user["perfis"][perfil] = perfil_data
    if not save_user(current_user["username"], current_user):
        raise HTTPException(status_code=500, detail="Erro ao salvar chat")

    return {"mensagens": mensagens}


@app.get("/download-pdf/{perfil}")
def download_pdf(perfil: str, current_user=Depends(get_current_user)):
    perfis = current_user.get("perfis") or {}
    perfil_data = perfis.get(perfil)
    if not perfil_data:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    mensagens = perfil_data.get("mensagens", [])
    plano_atual = ""
    for msg in reversed(mensagens):
        if msg.get("role") == "assistant" and "## 🧬" in msg.get("content", ""):
            plano_atual = msg["content"]
            break
    if not plano_atual and mensagens:
        plano_atual = mensagens[0].get("content", "")

    if not plano_atual:
        raise HTTPException(status_code=400, detail="Plano não disponível")

    pdf_bytes = gerar_pdf(plano_atual, perfil)
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Relatorio_{perfil.replace(' ', '_')}.pdf"})


@app.delete("/perfil/{nome}")
def delete_perfil(nome: str, current_user=Depends(get_current_user)):
    if not delete_profile(current_user["username"], nome):
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    return {"detail": "Perfil removido"}
