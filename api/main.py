# main.py - API HigIA
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import requests
import json
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path

from auth import get_login_url, handle_callback, get_user_from_token, logout_user
from engine import build_prompt, style_response
from sharepoint import ler_arquivos_da_pasta_ti, listar_arquivos_pasta, listar_raiz_sharepoint, listar_pasta
from config import (
    OLLAMA_URL, MODELO, HISTORY_FILE, REDIRECT_URI, CLIENT_ID, 
    TENANT_ID, BASE_URL, API_URL, DRIVE_ID
)

# ============================================
# CRIA O APP
# ============================================
app = FastAPI(title="HigIA - IA Corporativa")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# GERENCIAMENTO DE CONVERSAS
# ============================================
CONVERSATIONS_FILE = Path("D:/IA/api/conversations.json")

def load_conversations():
    if not CONVERSATIONS_FILE.exists():
        return {}
    try:
        with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao carregar conversas: {e}")
        return {}

def save_conversations(data):
    CONVERSATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erro ao salvar conversas: {e}")

CONVERSATIONS = load_conversations()

def get_conversations(user_id):
    return CONVERSATIONS.get(user_id, [])

def get_conversation(user_id, conversation_id):
    conversations = CONVERSATIONS.get(user_id, [])
    for conv in conversations:
        if conv.get("id") == conversation_id:
            return conv
    return None

def create_conversation(user_id, title="Nova Conversa"):
    if user_id not in CONVERSATIONS:
        CONVERSATIONS[user_id] = []
    
    new_conv = {
        "id": str(uuid.uuid4()),
        "title": title,
        "created_at": datetime.now().isoformat(),
        "messages": []
    }
    CONVERSATIONS[user_id].insert(0, new_conv)
    save_conversations(CONVERSATIONS)
    return new_conv

def add_message_to_conversation(user_id, conversation_id, role, content):
    conv = get_conversation(user_id, conversation_id)
    if conv:
        conv["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        if role == "user" and len([m for m in conv["messages"] if m["role"] == "user"]) == 1:
            conv["title"] = content[:50] + ("..." if len(content) > 50 else "")
        save_conversations(CONVERSATIONS)
        return True
    return False

def delete_conversation(user_id, conversation_id):
    if user_id in CONVERSATIONS:
        CONVERSATIONS[user_id] = [c for c in CONVERSATIONS[user_id] if c.get("id") != conversation_id]
        save_conversations(CONVERSATIONS)
        return True
    return False

# ============================================
# BUSCA RÁPIDA DE PASTA (match exato primeiro)
# ============================================
def buscar_pasta_rapida(access_token, nome_procurado):
    """Busca uma pasta diretamente na raiz e subpastas (sem carregar tudo)"""
    print(f"[SHAREPOINT] Busca rapida pela pasta: '{nome_procurado}'...")
    
    nome_limpo = nome_procurado.lower().replace('.', '').replace(' ', '').replace('-', '').replace('_', '')
    
    raiz = listar_raiz_sharepoint(access_token)
    if "error" in raiz:
        return None
    
    # PRIMEIRO: match EXATO na raiz
    for item in raiz.get("value", []):
        if "folder" in item:
            item_nome = item["name"].lower().replace('.', '').replace(' ', '').replace('-', '').replace('_', '')
            if nome_limpo == item_nome:
                print(f"[SHAREPOINT] Pasta encontrada na raiz (exata): {item['name']}")
                return {"nome": item["name"], "id": item["id"], "caminho": item["name"]}
    
    # SEGUNDO: match PARCIAL na raiz
    for item in raiz.get("value", []):
        if "folder" in item:
            item_nome = item["name"].lower().replace('.', '').replace(' ', '').replace('-', '').replace('_', '')
            if nome_limpo in item_nome and len(nome_limpo) >= 2:
                print(f"[SHAREPOINT] Pasta encontrada na raiz (parcial): {item['name']}")
                return {"nome": item["name"], "id": item["id"], "caminho": item["name"]}
    
    # TERCEIRO: match EXATO nas subpastas
    for item in raiz.get("value", []):
        if "folder" in item:
            try:
                sub = listar_pasta(access_token, item["id"])
                if "value" in sub:
                    for sub_item in sub["value"]:
                        if "folder" in sub_item:
                            sub_nome = sub_item["name"].lower().replace('.', '').replace(' ', '').replace('-', '').replace('_', '')
                            if nome_limpo == sub_nome:
                                caminho = f"{item['name']}/{sub_item['name']}"
                                print(f"[SHAREPOINT] Pasta encontrada na subpasta (exata): {caminho}")
                                return {"nome": sub_item["name"], "id": sub_item["id"], "caminho": caminho}
            except:
                pass
    
    # QUARTO: match PARCIAL nas subpastas
    for item in raiz.get("value", []):
        if "folder" in item:
            try:
                sub = listar_pasta(access_token, item["id"])
                if "value" in sub:
                    for sub_item in sub["value"]:
                        if "folder" in sub_item:
                            sub_nome = sub_item["name"].lower().replace('.', '').replace(' ', '').replace('-', '').replace('_', '')
                            if nome_limpo in sub_nome and len(nome_limpo) >= 2:
                                caminho = f"{item['name']}/{sub_item['name']}"
                                print(f"[SHAREPOINT] Pasta encontrada na subpasta (parcial): {caminho}")
                                return {"nome": sub_item["name"], "id": sub_item["id"], "caminho": caminho}
            except:
                pass
    
    return None

# ============================================
# MODELOS
# ============================================
class ChatData(BaseModel):
    token: str
    pergunta: str
    conversation_id: str = None

class NewConversationData(BaseModel):
    token: str
    title: str = "Nova Conversa"

class LogoutData(BaseModel):
    token: str

# ============================================
# ROTA RAIZ
# ============================================
@app.get("/")
def root():
    return {
        "message": "HigIA API - Online",
        "status": "ok",
        "model": MODELO,
        "docs": "/docs"
    }

# ============================================
# ROTAS DE AUTENTICAÇÃO
# ============================================
@app.get("/login")
def login_microsoft(maxAge: int = 3600):
    print(f"Iniciando login (maxAge={maxAge})")
    try:
        login_url = get_login_url()
        if "error" in login_url:
            raise HTTPException(status_code=500, detail=login_url["error"])
        return RedirectResponse(url=login_url["url"])
    except Exception as e:
        print(f"Erro no login: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/callback")
def callback(code: str):
    print("Callback recebido do Azure")
    result = handle_callback(code)
    
    if not result.get("ok"):
        print(f"Erro no callback: {result}")
        error_msg = result.get('error', 'Erro na autenticacao')
        return RedirectResponse(url=f"{BASE_URL}/ia/index.html?error={error_msg}")
    
    print(f"Login bem-sucedido para: {result.get('user')}")
    redirect_url = f"{BASE_URL}/ia/chat.html?token={result['token']}"
    return RedirectResponse(url=redirect_url)

@app.post("/logout")
def logout(data: LogoutData):
    print("Requisicao de logout")
    if logout_user(data.token):
        return {"success": True, "message": "Sessao encerrada com sucesso"}
    return {"success": False, "message": "Token nao encontrado"}

# ============================================
# ROTA DO CHAT
# ============================================
@app.post("/chat")
def chat(data: ChatData):
    print("\n" + "="*60)
    print("NOVA REQUISICAO DE CHAT")
    print("="*60)
    
    session = get_user_from_token(data.token)
    if not session:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    
    username = session.get("user", "unknown")
    user_id = session.get("claims", {}).get("oid", username)
    access_token = session.get("access_token")
    
    if not access_token:
        raise HTTPException(status_code=401, detail="Token de acesso invalido")
    
    print(f"Usuario: {username}")
    print(f"Pergunta: {data.pergunta}")
    
    conversation_id = data.conversation_id
    if not conversation_id:
        new_conv = create_conversation(user_id, "Nova Conversa")
        conversation_id = new_conv["id"]
    
    conv = get_conversation(user_id, conversation_id)
    if not conv:
        new_conv = create_conversation(user_id, "Nova Conversa")
        conversation_id = new_conv["id"]
        conv = new_conv
    
    historico = ""
    for msg in conv.get("messages", [])[-10:]:
        role = "Usuario" if msg['role'] == 'user' else "HigIA"
        historico += f"{role}: {msg['content']}\n"
    
    contexto = ""
    palavras_chave = [
        'arquivo', 'documento', 'pasta', 'lista', 'listar', 'quantos',
        'ferias', 'férias', 'beneficio', 'benefícios', 'pagamento', 
        'salario', 'salário', 'colaborador', 'funcionario', 'funcionários',
        'rh', 'recursos humanos', 'planilha', 'tabela', 'dados', 
        'relatorio', 'relatório', 'ti', 'backup', 'rede', 'nfs',
        'nota fiscal', 'nf', 'faturamento', 'transportadora',
        'sharepoint', 'pastas', 'ambiente', 'quais', 'ver', 'posso'
    ]
    
    precisa_contexto = any(palavra in data.pergunta.lower() for palavra in palavras_chave)
    
    if precisa_contexto:
        print("Buscando documentos no SharePoint...")
        try:
            nome_pasta = None
            match_pasta = re.search(r'pasta\s+([^\s,?]+)', data.pergunta, re.IGNORECASE)
            if match_pasta:
                nome_pasta = match_pasta.group(1)
            
            if nome_pasta:
                print(f"Procurando pasta especifica: {nome_pasta}")
                pasta_encontrada = buscar_pasta_rapida(access_token, nome_pasta)
                
                if pasta_encontrada:
                    arquivos_data = listar_arquivos_pasta(access_token, pasta_encontrada['id'])
                    if "value" in arquivos_data:
                        contexto = f"ARQUIVOS DA PASTA '{pasta_encontrada['caminho']}':\n"
                        tem_arquivos = False
                        for item in arquivos_data["value"]:
                            if "file" in item:
                                contexto += f"- {item['name']}\n"
                                tem_arquivos = True
                        if not tem_arquivos:
                            contexto += "(pasta vazia)"
                    else:
                        contexto = f"Erro ao listar arquivos da pasta {nome_pasta}"
                else:
                    contexto = f"Pasta '{nome_pasta}' nao encontrada. Use 'Quais pastas eu posso ver?' para ver todas as pastas disponiveis."
            else:
                contexto = ler_arquivos_da_pasta_ti(access_token)
            
            print(f"Contexto carregado: {len(contexto)} caracteres")
        except Exception as e:
            print(f"Erro SharePoint: {str(e)}")
            contexto = ""
    
    prompt = build_prompt(username, data.pergunta, contexto, historico)
    print(f"Prompt gerado: {len(prompt)} caracteres")
    
    print("Chamando Ollama...")
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODELO,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.1, "max_tokens": 2048}
            },
            timeout=(30, 180)
        )
        response.raise_for_status()
        result = response.json().get("message", {}).get("content", "")
        
        if not result:
            raise Exception("Resposta vazia do Ollama")
        
        print(f"Resposta gerada: {len(result)} caracteres")
        
        # Remove apresentacao se ja existe mensagem da HigIA no historico
        if "HigIA:" in historico:
            result = re.sub(r'Sou a HigIA[^.]*\.\s*', '', result)
            result = re.sub(r'assistente (inteligente )?da Cotton Line[^.]*\.\s*', '', result)
            result = re.sub(r'Como posso ajudar\??\s*', '', result)
        
        # Remove "Questão de seguimento" e qualquer texto extra
        result = re.sub(r'\n*Questão de seguimento.*', '', result, flags=re.DOTALL)
        result = re.sub(r'\n*Follow.?up.*', '', result, flags=re.DOTALL)
        result = re.sub(r'\n*USUARIO:.*', '', result, flags=re.DOTALL)
        result = re.sub(r'\n*HIGIA:.*', '', result, flags=re.DOTALL)
        result = result.strip()
        
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Servico de IA indisponivel")
    except Exception as e:
        print(f"Erro Ollama: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro no Ollama: {str(e)}")
    
    resposta_formatada = style_response(result)
    add_message_to_conversation(user_id, conversation_id, "user", data.pergunta)
    add_message_to_conversation(user_id, conversation_id, "assistant", resposta_formatada)
    
    return {"response": resposta_formatada, "conversation_id": conversation_id}

# ============================================
# ROTAS DE CONVERSAS
# ============================================
@app.get("/conversations")
def get_conversations_list(token: str):
    session = get_user_from_token(token)
    if not session:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    user_id = session.get("claims", {}).get("oid", session.get("user", "unknown"))
    conversations = get_conversations(user_id)
    result = [{"id": c.get("id"), "title": c.get("title", "Nova Conversa"), "created_at": c.get("created_at"), "message_count": len(c.get("messages", []))} for c in conversations]
    return {"conversations": result}

@app.post("/conversations/new")
def create_new_conversation(data: NewConversationData):
    session = get_user_from_token(data.token)
    if not session:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    user_id = session.get("claims", {}).get("oid", session.get("user", "unknown"))
    title = data.title or "Nova Conversa"
    new_conv = create_conversation(user_id, title)
    welcome_msg = "Olá! Tudo certo?<br><br>Sou a <b>HigIA</b>, a assistente inteligente da <b>Cotton Line</b>. Estou aqui para ajudar com documentos, processos internos e tirar dúvidas.<br><br>Como posso ajudar você hoje?"
    add_message_to_conversation(user_id, new_conv["id"], "assistant", welcome_msg)
    return {"conversation_id": new_conv["id"], "title": new_conv["title"]}

@app.get("/conversations/{conversation_id}")
def get_conversation_messages(token: str, conversation_id: str):
    session = get_user_from_token(token)
    if not session:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    user_id = session.get("claims", {}).get("oid", session.get("user", "unknown"))
    conv = get_conversation(user_id, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversa nao encontrada")
    return {"id": conv.get("id"), "title": conv.get("title"), "messages": conv.get("messages", [])}

@app.delete("/conversations/{conversation_id}")
def delete_conversation_endpoint(token: str, conversation_id: str):
    session = get_user_from_token(token)
    if not session:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    user_id = session.get("claims", {}).get("oid", session.get("user", "unknown"))
    if delete_conversation(user_id, conversation_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Conversa nao encontrada")

@app.get("/health")
def health():
    return {"status": "ok", "model": MODELO, "ollama": OLLAMA_URL, "timestamp": datetime.now().isoformat()}

# ============================================
# INICIA O SERVIDOR
# ============================================
if __name__ == "__main__":
    import uvicorn
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print("="*60)
    print(">>> INICIANDO API HigIA")
    print("="*60)
    print(f"    API URL: {API_URL}")
    print(f"    Modelo: {MODELO}")
    print(f"    Dados: D:/IA/api/")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8000, ssl_keyfile="C:/certs/htopp-s003.key", ssl_certfile="C:/certs/htopp-s003.crt")