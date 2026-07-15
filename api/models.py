from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


class AuthRequest(BaseModel):
    login: str = Field(..., description="Username or email")
    senha: str = Field(..., description="Password")


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, description="Unique username")
    email: EmailStr
    senha: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"


class PerfilDados(BaseModel):
    nome: str
    idade: int
    sexo: str
    peso: float
    altura: float
    alergias: str
    objetivo: str
    nivel: str


class PerfilCreateRequest(BaseModel):
    nome: str
    idade: int
    sexo: str
    peso: float
    altura: float
    alergias: Optional[str] = "Nenhuma"
    objetivo: str
    nivel: str


class ChatRequest(BaseModel):
    mensagem: str


class PerfilResponse(BaseModel):
    nome: str
    dados: PerfilDados
    mensagens: List[Dict[str, Any]] = []


class ErrorResponse(BaseModel):
    detail: str
