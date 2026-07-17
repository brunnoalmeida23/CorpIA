# engine.py
import re
from greetings import is_greeting

PERSONA = """
Voce e a HigIA, a assistente inteligente da Cotton Line.

REGRAS OBRIGATORIAS - SIGA SEMPRE:
0. NUNCA diga "Sou a HigIA" ou "assistente da Cotton Line" se ja existe mensagem da HigIA no historico
1. NUNCA invente informacoes, pastas, arquivos ou dados
2. Se nao encontrou nada no SharePoint, diga exatamente: "Nao encontrei arquivos nessa pasta."
3. Se nao tem certeza de algo, diga: "Nao tenho essa informacao."
4. Seja direto - maximo 3 frases curtas
5. Use **negrito** para destacar informacoes importantes
6. NAO use emojis
7. NAO use frases como "Vamos la", "Deixe-me verificar"
8. NAO repita sua apresentacao depois da primeira mensagem
9. Se o historico ja tem mensagens da HigIA, NAO se apresente - apenas responda
10. NUNCA adicione perguntas de seguimento, sugestoes ou continue a conversa por conta propria. Apenas responda exatamente o que foi perguntado.
11. NUNCA invente URLs, links ou formas de acesso a arquivos. Apenas liste o que foi encontrado no SharePoint.

QUANDO FOR SAUDACAO NA PRIMEIRA MENSAGEM:
- Apresente-se: "Sou a HigIA, assistente da Cotton Line. Como posso ajudar?"

QUANDO NAO ENCONTRAR ARQUIVOS:
- Diga: "Nao encontrei arquivos nessa pasta. Verifique se voce tem permissao de acesso."

QUANDO PERGUNTAREM ALGO QUE VOCE NAO SABE:
- Diga: "Nao tenho essa informacao. Posso ajudar com outra coisa?"

EXEMPLOS:
- "Encontrei **17 arquivos** na pasta TI:\n- Arquivo1.xlsx\n- Arquivo2.pdf"
- "Nao encontrei arquivos nessa pasta. Verifique se voce tem permissao de acesso."
- "Python e uma linguagem de programacao usada para criar sistemas e automatizar tarefas."
"""

def build_prompt(user, pergunta, contexto, historico):
    is_first = not historico or "Usuario:" not in historico
    
    print(f"\n[ENGINE] Verificando pergunta: '{pergunta}'")
    print(f"[ENGINE] is_greeting() = {is_greeting(pergunta)}")
    print(f"[ENGINE] is_first() = {is_first}")
    print(f"[ENGINE] Historico: {historico[:100] if historico else 'VAZIO'}...")
    
    # ============================================
    # SAUDAÇÃO
    # ============================================
    if is_greeting(pergunta):
        print("[ENGINE] Detectado como SAUDAÇÃO!")
        if not is_first:
            prompt = f"""
{PERSONA}

HISTORICO DA CONVERSA:
{historico}

USUARIO: {user}
PERGUNTA: {pergunta}

INSTRUCAO: Responda a saudacao de forma breve (1 frase). NAO se apresente pois a conversa ja iniciou. Nao use emojis.
RESPOSTA:"""
            return prompt
        
        prompt = f"""
{PERSONA}

HISTORICO DA CONVERSA:
{historico if historico else "Nenhuma conversa anterior."}

USUARIO: {user}
PERGUNTA: {pergunta}

INSTRUCAO: 
1. Saudacao na primeira mensagem. Apresente-se brevemente (1-2 frases).
2. Pergunte como pode ajudar.
3. Nao use emojis.

RESPOSTA:"""
        return prompt
    
    print("[ENGINE] NÃO é saudação, processando normalmente...")
    
    # ============================================
    # PALAVRAS-CHAVE
    # ============================================
    palavras_chave = [
        'arquivo', 'documento', 'pasta', 'lista', 'listar', 'quantos',
        'ferias', 'férias', 'beneficio', 'benefícios', 'pagamento', 
        'salario', 'salário', 'colaborador', 'funcionario', 'funcionários',
        'rh', 'recursos humanos', 'planilha', 'tabela', 'dados', 
        'relatorio', 'relatório', 'ti', 'backup', 'rede', 'nfs',
        'nota fiscal', 'nf', 'faturamento', 'transportadora',
        'sharepoint', 'pastas', 'ambiente', 'quais', 'ver', 'posso'
    ]
    
    precisa_contexto = any(palavra in pergunta.lower() for palavra in palavras_chave)
    
    # ============================================
    # ARQUIVO ESPECÍFICO
    # ============================================
    nome_arquivo = None
    padroes = [
        r'arquivo\s+([^\s,.?]+)',
        r'([^\s,.?]+)\.(txt|docx|pdf|xlsx|ods|rar|zip|exe|png|jpg)',
        r'conteudo\s+do\s+([^\s,.?]+)',
        r'dentro\s+do\s+([^\s,.?]+)',
        r'no\s+arquivo\s+([^\s,.?]+)'
    ]
    for padrao in padroes:
        match = re.search(padrao, pergunta, re.IGNORECASE)
        if match:
            nome_arquivo = match.group(1)
            break
    
    # ============================================
    # CASO 1: ARQUIVO ESPECÍFICO
    # ============================================
    if nome_arquivo:
        conteudo_extraido = ""
        if contexto:
            padrao_arquivo = rf"ARQUIVO: {re.escape(nome_arquivo)}\n(.*?)(?=\nARQUIVO:|$)"
            match = re.search(padrao_arquivo, contexto, re.DOTALL | re.IGNORECASE)
            if match:
                conteudo_extraido = match.group(1).strip()
        
        if conteudo_extraido:
            prompt = f"""
{PERSONA}

HISTORICO: {historico if historico else "Nenhuma conversa anterior."}
USUARIO: {user}
PERGUNTA: {pergunta}

CONTEUDO DO ARQUIVO {nome_arquivo}:
{conteudo_extraido}

INSTRUCAO: Mostre APENAS o conteudo do arquivo. NAO se apresente. Nao invente nada. Seja direto. NAO adicione perguntas extras.
RESPOSTA:"""
        else:
            prompt = f"""
{PERSONA}

HISTORICO: {historico if historico else "Nenhuma conversa anterior."}
USUARIO: {user}
PERGUNTA: {pergunta}

INSTRUCAO: Diga que o arquivo nao foi encontrado. Sugira verificar permissoes. NAO se apresente. Nao invente nada. Maximo 2 frases. NAO adicione perguntas extras.
RESPOSTA:"""
        return prompt
    
    # ============================================
    # CASO 2: LISTA DE ARQUIVOS OU PASTAS
    # ============================================
    if precisa_contexto and contexto:
        if "ARQUIVOS DA PASTA" in contexto:
            prompt = f"""
{PERSONA}

HISTORICO: {historico if historico else "Nenhuma conversa anterior."}
USUARIO: {user}
PERGUNTA: {pergunta}

{contexto}

INSTRUCAO: Mostre APENAS os arquivos da pasta listada acima. NAO liste outras pastas. NAO invente nada. NAO se apresente. NAO adicione perguntas extras. Seja direto. Use **negrito** para o nome da pasta.
RESPOSTA:"""
            return prompt
        
        nomes = []
        for linha in contexto.split('\n'):
            if linha.startswith('- '):
                nome = linha[2:].strip()
                if nome and not nome.startswith('---'):
                    nomes.append(nome)
        
        if nomes:
            lista_formatada = "\n".join([f"- {nome}" for nome in nomes])
            prompt = f"""
{PERSONA}

HISTORICO: {historico if historico else "Nenhuma conversa anterior."}
USUARIO: {user}
PERGUNTA: {pergunta}

LISTA DE PASTAS:
{lista_formatada}

INSTRUCAO: Mostre as pastas de forma organizada. NAO invente nada. NAO se apresente. NAO adicione perguntas extras. Va direto para a lista.
RESPOSTA:"""
        else:
            prompt = f"""
{PERSONA}

HISTORICO: {historico if historico else "Nenhuma conversa anterior."}
USUARIO: {user}
PERGUNTA: {pergunta}

INSTRUCAO: Diga que nao encontrou pastas ou arquivos. NAO invente nada. NAO se apresente. NAO adicione perguntas extras. Maximo 2 frases.
RESPOSTA:"""
        return prompt
    
    # ============================================
    # CASO 3: PRIMEIRA MENSAGEM DO USUARIO
    # ============================================
    if is_first:
        prompt = f"""
{PERSONA}

HISTORICO: {historico if historico else "Nenhuma conversa anterior."}
USUARIO: {user}
PERGUNTA: {pergunta}

INSTRUCAO: Primeira mensagem do usuario. Responda direto a pergunta. NAO se apresente. NAO invente nada. NAO adicione perguntas extras. Use **negrito** se util.
RESPOSTA:"""
        return prompt
    
    # ============================================
    # CASO 4: CONVERSA NORMAL
    # ============================================
    prompt = f"""
{PERSONA}

HISTORICO: {historico if historico else "Nenhuma conversa anterior."}
USUARIO: {user}
PERGUNTA: {pergunta}

INSTRUCAO: Responda de forma natural e direta. NAO se apresente. Nao invente nada. NAO adicione perguntas extras. Maximo 3 frases. Nao use emojis.
RESPOSTA:"""
    
    return prompt

def style_response(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    text = text.replace("\n", "<br>")
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'<br>- (.*?)(?=<br>|$)', r'<br>• \1', text)
    return text