# greetings.py
import re

# Lista de saudações em português (e variações)
SAUDACOES = {
    # Saudações formais
    'olá', 'ola', 'oi', 'bom dia', 'boa tarde', 'boa noite', 
    'boa tarde', 'boa noite', 'bom dia',
    
    # Saudações informais
    'salve', 'fala', 'opa', 'eae', 'e aí', 'eai', 
    'beleza', 'tranquilo', 'suave', 'show',
    
    # Gírias
    'coé', 'coe', 'fala aí', 'falai', 'fala tu',
    'o que ce diz', 'o que cê diz', 'como vai',
    
    # Saudações em inglês
    'hello', 'hi', 'hey', 'howdy', 'greetings',
    
    # Variações com pontuação
    'oi!', 'olá!', 'salve!', 'opa!', 'eae!', 'beleza?', 'tranquilo?'
}

# Padrões regex para detectar saudações isoladas
PADROES_SAUDACAO = [
    r'^(oi|olá|ola|salve|fala|opa|eae|beleza|tranquilo|hello|hi|hey|coé|coe)([!?.,]|$|\s|$)',
    r'^(bom dia|boa tarde|boa noite|bom dia|boa tarde)([!?.,]|$|\s|$)',
    r'^(e aí|eai|como vai|tudo bem)([!?.,]|$|\s|$)',
]

def is_greeting(text):
    """
    Detecta se o texto é APENAS uma saudação (não uma pergunta)
    """
    text_lower = text.lower().strip()
    
    # Remove pontuação no final
    text_clean = re.sub(r'[!?.,;:]+$', '', text_lower).strip()
    
    # Se tiver mais de 5 palavras, provavelmente não é só saudação
    if len(text_clean.split()) > 5:
        return False
    
    # Verifica se a mensagem é exatamente uma saudação
    if text_clean in SAUDACOES:
        return True
    
    # Verifica padrões regex
    for padrao in PADROES_SAUDACAO:
        if re.match(padrao, text_lower):
            return True
    
    return False

def get_greeting_type(text):
    """
    Retorna o tipo de saudação para respostas mais naturais
    """
    text_lower = text.lower().strip()
    
    if any(word in text_lower for word in ['bom dia', 'boa tarde', 'boa noite']):
        return 'formal'
    elif any(word in text_lower for word in ['salve', 'fala', 'opa', 'eae', 'coé']):
        return 'informal'
    elif any(word in text_lower for word in ['hello', 'hi', 'hey']):
        return 'ingles'
    else:
        return 'normal'