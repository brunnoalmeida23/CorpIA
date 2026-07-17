# auth.py
import msal
import uuid
import json
import os
import time
from config import (
    CLIENT_ID,
    CLIENT_SECRET,
    TENANT_ID,
    REDIRECT_URI,
    SESSIONS_FILE
)

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

# Tempo de expiração da sessão (1 hora)
SESSION_TIMEOUT = 3600  # 60 minutos

def carregar_sessoes():
    if not os.path.exists(SESSIONS_FILE):
        return {}
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Limpa sessões expiradas ao carregar
            data = limpar_sessoes_expiradas(data)
            return data
    except Exception:
        return {}

def limpar_sessoes_expiradas(data):
    """Remove sessões expiradas"""
    if not data:
        return {}
    
    agora = time.time()
    sessoes_ativas = {}
    
    for token, sessao in data.items():
        created_at = sessao.get("created_at", 0)
        if agora - created_at < SESSION_TIMEOUT:
            sessoes_ativas[token] = sessao
        else:
            print(f"🗑️ Sessão expirada removida: {token[:20]}...")
    
    return sessoes_ativas

def salvar_sessoes(data):
    try:
        os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar sessao: {str(e)}")

# Cache em memória (não persiste após reiniciar o servidor)
SESSION_CACHE = carregar_sessoes()

def _sync_cache():
    global SESSION_CACHE
    SESSION_CACHE = carregar_sessoes()

def _build_msal_app():
    try:
        return msal.ConfidentialClientApplication(
            client_id=CLIENT_ID,
            authority=AUTHORITY,
            client_credential=CLIENT_SECRET
        )
    except Exception as e:
        print(f"Erro ao criar MSAL app: {str(e)}")
        raise

def is_session_valid(session_data):
    """Verifica se a sessão ainda é válida (não expirou)"""
    if not session_data:
        return False
    
    created_at = session_data.get("created_at")
    if not created_at:
        return False
    
    # Verifica se passou mais de 1 hora
    if time.time() - created_at > SESSION_TIMEOUT:
        return False
    
    return True

def get_login_url():
    try:
        app = _build_msal_app()
        
        scopes = [
            "User.Read",
            "Sites.Read.All", 
            "Files.Read.All"
        ]
        
        auth_url = app.get_authorization_request_url(
            scopes=scopes,
            redirect_uri=REDIRECT_URI,
            prompt="select_account"
        )
        
        return {"url": auth_url}
        
    except Exception as e:
        print(f"Erro em get_login_url: {str(e)}")
        return {"error": str(e), "url": None}

def handle_callback(code: str):
    global SESSION_CACHE  # <-- ADICIONE ESTA LINHA
    
    try:
        app = _build_msal_app()
        
        scopes = [
            "User.Read",
            "Sites.Read.All",
            "Files.Read.All"
        ]
        
        result = app.acquire_token_by_authorization_code(
            code=code,
            scopes=scopes,
            redirect_uri=REDIRECT_URI
        )

        if "access_token" not in result:
            return {
                "ok": False,
                "error": result.get("error_description", result)
            }

        claims = result.get("id_token_claims", {})
        username = claims.get("preferred_username", "unknown")

        # Gera um token de sessão único
        session_token = str(uuid.uuid4())
        
        # Salva na sessão (apenas dados necessários, sem token de acesso do usuário)
        SESSION_CACHE[session_token] = {
            "user": username,
            "access_token": result["access_token"],
            "refresh_token": result.get("refresh_token", ""),
            "claims": claims,
            "created_at": time.time(),
            "last_activity": time.time()
        }

        # Limpa sessões expiradas antes de salvar
        SESSION_CACHE = limpar_sessoes_expiradas(SESSION_CACHE)
        salvar_sessoes(SESSION_CACHE)

        print(f"✅ Nova sessão criada: {session_token[:20]}... para {username}")
        print(f"📊 Total de sessões ativas: {len(SESSION_CACHE)}")

        return {
            "ok": True,
            "token": session_token,
            "user": username
        }
        
    except Exception as e:
        print(f"Erro em handle_callback: {str(e)}")
        return {
            "ok": False,
            "error": str(e)
        }

def get_user_from_token(token: str):
    """Valida o token e retorna os dados da sessão"""
    if not token:
        return None
    
    _sync_cache()
    session_data = SESSION_CACHE.get(token)
    
    if not session_data:
        print(f"❌ Token não encontrado: {token[:20]}...")
        return None
    
    # Verifica se a sessão expirou
    if not is_session_valid(session_data):
        print(f"⏰ Sessão expirada para token: {token[:20]}...")
        # Remove a sessão expirada
        SESSION_CACHE.pop(token, None)
        salvar_sessoes(SESSION_CACHE)
        return None
    
    # Atualiza última atividade
    session_data["last_activity"] = time.time()
    SESSION_CACHE[token] = session_data
    
    return session_data

def logout_user(token: str):
    """Remove a sessão do usuário (logout)"""
    if token in SESSION_CACHE:
        user = SESSION_CACHE[token].get("user", "unknown")
        SESSION_CACHE.pop(token, None)
        salvar_sessoes(SESSION_CACHE)
        print(f"👋 Logout: {user} - Sessão removida")
        return True
    return False

def refresh_access_token(refresh_token: str):
    """Renova o access_token usando o refresh_token"""
    try:
        app = _build_msal_app()
        result = app.acquire_token_by_refresh_token(
            refresh_token,
            scopes=[
                "User.Read",
                "Sites.Read.All", 
                "Files.Read.All"
            ]
        )
        
        if "access_token" in result:
            return {
                "ok": True,
                "access_token": result["access_token"],
                "refresh_token": result.get("refresh_token", refresh_token)
            }
        else:
            return {
                "ok": False,
                "error": result.get("error_description", "Erro ao renovar token")
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}