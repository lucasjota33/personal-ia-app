import requests
from typing import Any, Dict, Optional
from .config import settings

BASE_URL = (
    f"https://firestore.googleapis.com/v1/projects/{settings.firebase_project_id}"
    "/databases/(default)/documents/usuarios"
)


def _to_firestore(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return {"mapValue": {"fields": {str(k): _to_firestore(v) for k, v in value.items()}}}
    if isinstance(value, (list, tuple)):
        return {"arrayValue": {"values": [_to_firestore(v) for v in value]}}
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if value is None:
        return {"nullValue": None}
    return {"stringValue": str(value)}


def _from_firestore(value: Dict[str, Any]) -> Any:
    if "mapValue" in value:
        return {k: _from_firestore(v) for k, v in value["mapValue"].get("fields", {}).items()}
    if "arrayValue" in value:
        return [_from_firestore(v) for v in value["arrayValue"].get("values", [])]
    if "stringValue" in value:
        return value["stringValue"]
    if "integerValue" in value:
        try:
            return int(value["integerValue"])
        except ValueError:
            return value["integerValue"]
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "booleanValue" in value:
        return value["booleanValue"]
    if "nullValue" in value:
        return None
    return None


def _get_doc_url(username: str) -> str:
    return f"{BASE_URL}/{username}"


def _build_payload(document: Dict[str, Any]) -> Dict[str, Any]:
    return {"fields": {str(k): _to_firestore(v) for k, v in document.items()}}


def get_user(username: str) -> Optional[Dict[str, Any]]:
    try:
        url = f"{_get_doc_url(username)}?key={settings.firebase_api_key}"
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            return None
        fields = response.json().get("fields", {})
        return {k: _from_firestore(v) for k, v in fields.items()}
    except Exception:
        return None


def list_users() -> Dict[str, Dict[str, Any]]:
    """
    Varre a coleção inteira. Retorna dict vazio em caso de erro
    (403, timeout, etc.) em vez de lançar exceção.
    """
    try:
        url = f"{BASE_URL}?key={settings.firebase_api_key}"
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            return {}
        result: Dict[str, Dict[str, Any]] = {}
        for doc in response.json().get("documents", []):
            username = doc.get("name", "").split("/")[-1]
            fields = doc.get("fields", {})
            result[username] = {k: _from_firestore(v) for k, v in fields.items()}
        return result
    except Exception:
        return {}


def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    try:
        for username, user in list_users().items():
            if user.get("email", "").lower() == email.lower():
                return {"username": username, **user}
    except Exception:
        pass
    return None


def find_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    try:
        for username, user in list_users().items():
            if user.get("token") == token:
                return {"username": username, **user}
    except Exception:
        pass
    return None


def save_user(username: str, user_data: Dict[str, Any]) -> bool:
    try:
        payload = _build_payload(user_data)
        url = f"{_get_doc_url(username)}?key={settings.firebase_api_key}"
        response = requests.patch(url, json=payload, timeout=20)
        if response.status_code == 404:
            create_url = f"{BASE_URL}?documentId={username}&key={settings.firebase_api_key}"
            response = requests.post(create_url, json=payload, timeout=20)
        return response.status_code in (200, 201)
    except Exception:
        return False


def delete_profile(username: str, profile_name: str) -> bool:
    try:
        user = get_user(username)
        if not user:
            return False
        profiles = user.get("perfis", {}) or {}
        profiles.pop(profile_name, None)
        user["perfis"] = profiles
        return save_user(username, user)
    except Exception:
        return False