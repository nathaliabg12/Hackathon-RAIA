import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import re
import json

# Inicializa cliente OpenAI
client = OpenAI()

app = FastAPI()

# Estado do jogo em memória (simples)
games = {}

# Estrutura do request de resposta
class AnswerRequest(BaseModel):
    game_id: str
    order: list[int]  # ordem das manchetes escolhida pelo usuário


# --- Funções auxiliares ---

def generate_headlines(fact: str):
    """
    Usa a API da OpenAI para gerar 4 manchetes com diferentes vieses.
    """
    prompt = f"""
Você é um gerador de manchetes. 
Com base no fato objetivo abaixo, crie 4 manchetes, cada uma com um viés específico:

Fato: "{fact}"

1. Neutra – apresente o fato de forma clara e objetiva.
2. Sensacionalista – exagere ou dramatize o fato para causar impacto.
3. Omissiva – omita detalhes importantes ou mostre só parte do fato.
4. Manipuladora – distorça o fato para induzir interpretação enviesada.

Responda no formato JSON com as chaves: neutra, sensacionalista, omissiva, manipuladora.
"""
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )
    content = response.choices[0].message.content
    
    print("Generated headlines:", content)
    
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise HTTPException(status_code=500, detail="Erro ao extrair JSON do GPT")

    try:
        headlines = json.loads(match.group())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao converter JSON: {e}")

    return headlines


# --- Endpoints ---

@app.post("/start")
def start_game():
    """Inicia um novo jogo."""
    game_id = str(random.randint(1000, 9999))
    games[game_id] = {"round": 0, "score": 0, "facts": []}
    return {"game_id": game_id, "message": "Jogo iniciado!"}


@app.get("/round/{game_id}")
def new_round(game_id: str):
    """Gera uma nova rodada com fato e manchetes."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")

    # Noticias que vêm da Nathália
    facts = [
        "A vacina contra COVID-19 reduz em 90% o risco de hospitalização",
        "A taxa de desemprego caiu 2% no último trimestre",
        "Um novo recorde de temperatura foi registrado no Ártico",
        "O PIB do país cresceu 3% no último ano",
        "Um asteroide passou a 7 milhões de km da Terra",
        "A poluição do ar nas grandes cidades caiu 15% em 2024",
        "Cientistas descobriram um novo exoplaneta parecido com a Terra",
        "O uso de energia solar aumentou 25% em 2025",
        "O consumo de carne vermelha caiu 10% no Brasil",
        "O transporte público recebeu investimento de 5 bilhões em 2025"
    ]

    game = games[game_id]
    if game["round"] >= 10:
        return {"message": "Jogo já terminou."}

    fact = facts[game["round"]]
    headlines = generate_headlines(fact)

    # embaralha as manchetes para o usuário ordenar
    shuffled = list(headlines.items())
    random.shuffle(shuffled)

    print("Shuffled headlines:", shuffled)

    # salva a rodada
    game["round"] += 1
    game["current"] = {
        "fact": fact,
        "headlines": shuffled,
        "answer": ["neutra", "sensacionalista", "omissiva", "manipuladora"]
    }

    return {"round": game["round"], "fact": fact, "headlines": shuffled}


@app.post("/answer")
def submit_answer(request: AnswerRequest):
    """Recebe a ordem do usuário e calcula pontuação da rodada."""
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")

    game = games[request.game_id]
    if "current" not in game:
        raise HTTPException(status_code=400, detail="Nenhuma rodada ativa")

    correct_order = game["current"]["answer"]

    # o usuário envia ordem como lista de índices [0,1,2,3]
    headlines = game["current"]["headlines"]
    user_order = [headlines[i][0] for i in request.order]

    # calcula pontuação (quanto mais próximo, maior a nota)
    score = sum([1 for i in range(4) if user_order[i] == correct_order[i]])
    game["score"] += score

    # limpa rodada atual
    del game["current"]

    return {"round_score": score, "total_score": game["score"]}


@app.get("/finish/{game_id}")
def finish_game(game_id: str):
    """Finaliza o jogo e mostra a pontuação."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")

    score = games[game_id]["score"]
    del games[game_id]

    explanation = {
        "neutra": "Apresenta o fato de forma objetiva, sem exageros.",
        "sensacionalista": "Exagera ou dramatiza o fato para chamar atenção.",
        "omissiva": "Esconde informações relevantes ou mostra só parte do fato.",
        "manipuladora": "Distorce o fato para induzir interpretação enviesada."
    }

    return {"final_score": score, "max_score": 40, "explanation": explanation}
