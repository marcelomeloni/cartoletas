
import sys
import random
import os
import math
from datetime import datetime
import subprocess



# Função para garantir que o pygame esteja instalado
def instalar_dependencia(pacote):
    try:
        __import__(pacote)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pacote])

# Verificar e instalar o pygame
instalar_dependencia('pygame')
import pygame
import pygame.locals as pl

# Matriz de pontuação fixa: SCORE_MATRIX[dificuldade][regiao]
SCORE_MATRIX = {
    0: {0: 5, 1: 5, 2: 10, 3: 10, 4: 15},   # Fácil
    1: {0: 10, 1: 10, 2: 15, 3: 20, 4: 25},  # Médio
    2: {0: 15, 1: 20, 2: 25, 3: 30, 4: 30}   # Difícil
}
RANKING_FILE = 'rankings.txt'
FLIP_DELAY = 500  # Tempo para verificar o par em milissegundos
COR_DESTAQUE = (200, 200, 200)  # Cor ao passar o mouse
TEMPO_JOGO = 60000
COR_FUNDO = (255, 225, 201)
COR_BOTAO = (254, 115, 2)  # Cor laranja #fe7302 em RGB
COR_TEXTO = (0, 0, 0)       # Preto
# Constantes de dificuldade: nome, número de pares, pesos regionais
DIFICULDADES = {
    0: ('Fácil', 9,  {1:50, 0:20, 2:10, 3:10, 4:10}),
    1: ('Médio', 12, {1:25, 0:25, 2:20, 3:15, 4:15}),
    2: ('Difícil',15, {1:10, 0:20, 2:25, 3:25, 4:20})
}
NOTIFICACOES_PATH = os.path.join('assets', 'images', 'notificacoes')
SONS_PATH = os.path.join('assets', 'sounds')
MARCOS_PONTUACAO = [5, 10, 15, 20, 25, 30]
# Pasta de cards
CARDS_PATH = os.path.join('assets', 'images', 'cards')

class Notificacao:
    def __init__(self):
        self.imagens = {}
        self.som_notificacao = None
        self.notificacao_atual = None
        self.tempo_exibicao = 1000  # 1 segundo
        self.tempo_inicio = 0
        self.escala = 0.15

        # Carregar imagens para todos os valores possíveis de pontos
        todos_pontos = set()
        for diff in SCORE_MATRIX.values():
            todos_pontos.update(diff.values())
        
        for pontos in todos_pontos:
            img_path = os.path.join(NOTIFICACOES_PATH, f'{pontos}pts.png')
            if os.path.exists(img_path):
                img = pygame.image.load(img_path).convert_alpha()
                w = int(img.get_width() * self.escala)
                h = int(img.get_height() * self.escala)
                self.imagens[pontos] = pygame.transform.scale(img, (w, h))

        # Carregar som
        sound_path = os.path.join(SONS_PATH, 'notificacao.wav')
        if os.path.exists(sound_path):
            try:
                self.som_notificacao = pygame.mixer.Sound(sound_path)
                self.som_notificacao.set_volume(0.5)
            except Exception as e:
                print(f"Erro no áudio: {e}")

    def disparar_notificacao(self, pontos):
        """Dispara notificação para qualquer valor de pontos"""
        if pontos in self.imagens:
            self.notificacao_atual = self.imagens[pontos]
            self.tempo_inicio = pygame.time.get_ticks()
            print(f"Notificação disparada para {pontos} pontos")  # Debug
        
        if self.som_notificacao:
            try:
                self.som_notificacao.stop()
                self.som_notificacao.play()
            except Exception as e:
                print(f"Erro ao tocar som: {e}")

    def update(self):
        if self.notificacao_atual and (pygame.time.get_ticks() - self.tempo_inicio) > self.tempo_exibicao:
            self.notificacao_atual = None

    def draw(self, tela):
        if self.notificacao_atual:
            pos_x = tela.get_width() - self.notificacao_atual.get_width() - 20
            pos_y = tela.get_height() - self.notificacao_atual.get_height() - 20
            tela.blit(self.notificacao_atual, (pos_x, pos_y))
def get_time_ids(regiao_id):
    ids = set()
    for fname in os.listdir(CARDS_PATH):
        if fname.startswith(f"{regiao_id}_"):
            parts = fname.split('_')
            if len(parts) >= 3 and parts[0] == str(regiao_id) and parts[2].split('.')[0] in ['0', '1']:
                time_id = parts[1]
                if time_id.isdigit():
                    time_id = int(time_id)
                    # Verifica se ambos os tipos existem
                    if (os.path.exists(os.path.join(CARDS_PATH, f"{regiao_id}_{time_id}_0.png")) and
                        os.path.exists(os.path.join(CARDS_PATH, f"{regiao_id}_{time_id}_1.png"))):
                        ids.add(time_id)
    return sorted(ids)
class Carta:
    DEFAULT_BACK = os.path.join(CARDS_PATH, 'default.png')

    def __init__(self, regiao_id, time_id, tipo):
        self.regiao_id = regiao_id
        self.time_id = time_id
        self.tipo = tipo  # 0 para nome, 1 para logo

        # Carregar verso (default.png)
        if not os.path.exists(Carta.DEFAULT_BACK):
            raise FileNotFoundError(f"Arquivo de verso padrão não encontrado: {Carta.DEFAULT_BACK}")
        raw_back = pygame.image.load(Carta.DEFAULT_BACK).convert_alpha()

        # Carregar frente (regiao_time_tipo.png)
        front_file = f"{regiao_id}_{time_id}_{tipo}.png"
        front_path = os.path.join(CARDS_PATH, front_file)
        if not os.path.exists(front_path):
            raise FileNotFoundError(f"Frente não encontrada: {front_path}")
        raw_front = pygame.image.load(front_path).convert_alpha()

        self.raw_back = raw_back
        self.raw_front = raw_front
        self.image_back = None
        self.image_front = None
        self.rect = None
        self.face_up = False
        self.matched = False

    def set_rect_and_scale(self, cell_rect):
        # Reduzir o padding interno para aproveitar mais espaço
        max_w, max_h = cell_rect.width - 4, cell_rect.height - 4  # Reduzi de 10 para 4
        
        for name, raw in [('back', self.raw_back), ('front', self.raw_front)]:
            w, h = raw.get_size()
            scale = min(max_w / w, max_h / h)
            new_size = (int(w * scale), int(h * scale))
            img = pygame.transform.scale(raw, new_size)
            setattr(self, f'image_{name}', img)
        
        # Centralizar a carta na célula
        self.rect = self.image_back.get_rect(center=cell_rect.center)
    def draw(self, surf, mouse_pos):
        img = self.image_front if (self.face_up or self.matched) else self.image_back
        surf.blit(img, self.rect.topleft)
        
        # Destacar carta com hover
        if not self.matched and self.rect.collidepoint(mouse_pos):
            highlight = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            highlight.fill((*COR_DESTAQUE, 30))
            surf.blit(highlight, self.rect.topleft)

    def flip(self):
        if not self.matched:
            self.face_up = not self.face_up
def init_pygame():
    pygame.init()
    pygame.mixer.pre_init(44100, -16, 2, 512)  # Parâmetros otimizados
    pygame.mixer.init()
    info = pygame.display.Info()
    return pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
def tela_inicial(tela):
    logo = pygame.image.load(os.path.join('assets', 'images', 'logo.png'))
    logo = pygame.transform.scale(logo, (600, 225))
    
    btn_play = pygame.image.load(os.path.join('assets', 'images', 'button_play.png'))
    btn_ranking = pygame.image.load(os.path.join('assets', 'images', 'ranking.png'))
    
    # Ajuste das posições com mais espaçamento (80 -> 100, 180 -> 220)
    btn_play_rect = btn_play.get_rect(center=(tela.get_width()//2, tela.get_height()//2 + 100))
    btn_ranking_rect = btn_ranking.get_rect(center=(tela.get_width()//2, tela.get_height()//2 + 320))
    
    while True:
        for ev in pygame.event.get():
            if ev.type == pl.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pl.MOUSEBUTTONDOWN:
                if btn_play_rect.collidepoint(ev.pos):
                    return 'play'
                elif btn_ranking_rect.collidepoint(ev.pos):
                    return 'ranking'
        
        tela.fill(COR_FUNDO)
        tela.blit(logo, ((tela.get_width()-logo.get_width())//2, 80))
        tela.blit(btn_play, btn_play_rect)
        tela.blit(btn_ranking, btn_ranking_rect)
        pygame.display.flip()
def tela_ranking(tela):
    rankings = carregar_rankings()
    fonte_titulo = pygame.font.SysFont(None, 48)
    fonte_cabecalho = pygame.font.SysFont(None, 36, bold=True)
    fonte_itens = pygame.font.SysFont(None, 32)
    
    btn_voltar = pygame.image.load(os.path.join('assets', 'images', 'button_voltar.png'))
    btn_voltar_rect = btn_voltar.get_rect(bottomleft=(20, tela.get_height()-20))
    
    colunas = [
        {"x": 50, "dificuldade": "Fácil", "cor": (0, 150, 0)},
        {"x": tela.get_width()//2 - 150, "dificuldade": "Médio", "cor": (255, 165, 0)},
        {"x": tela.get_width() - 350, "dificuldade": "Difícil", "cor": (255, 0, 0)}
    ]
    
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN and btn_voltar_rect.collidepoint(ev.pos):
                return
        
        tela.fill(COR_FUNDO)
        
        # Título principal
        titulo = fonte_titulo.render("Ranking por Dificuldade", True, COR_TEXTO)
        tela.blit(titulo, ((tela.get_width()-titulo.get_width())//2, 20))
        
        y_base = 100
        for coluna in colunas:
            dificuldade = coluna["dificuldade"]
            dados = rankings[dificuldade]
            
            # Cabeçalho da coluna
            cabecalho = fonte_cabecalho.render(dificuldade, True, coluna["cor"])
            tela.blit(cabecalho, (coluna["x"], y_base))
            
            # Linha de divisão
            pygame.draw.line(tela, coluna["cor"], (coluna["x"], y_base + 40), 
                           (coluna["x"] + 300, y_base + 40), 2)
            
            # Itens do ranking
            y = y_base + 60
            for i, (nome, pontos, data) in enumerate(dados):
                texto = fonte_itens.render(f"{i+1}. {nome[:15]} - {pontos} pts", True, COR_TEXTO)
                tela.blit(texto, (coluna["x"], y))
                y += 40
                
                if y > tela.get_height() - 100:  # Evitar ultrapassar a tela
                    break
        
        # Botão voltar
        tela.blit(btn_voltar, btn_voltar_rect)
        pygame.display.flip()
def input_nome(tela):
    nome = ""
    fonte = pygame.font.SysFont(None, 48)
    ativo = True
    
    while ativo:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_RETURN and nome.strip() != "":
                    ativo = False
                elif ev.key == pygame.K_BACKSPACE:
                    nome = nome[:-1]
                else:
                    if len(nome) < 20:
                        nome += ev.unicode
        
        tela.fill(COR_FUNDO)
        texto = fonte.render("Digite seu nome:", True, COR_TEXTO)
        tela.blit(texto, ((tela.get_width()-texto.get_width())//2, tela.get_height()//2 - 50))
        
        input_box = fonte.render(nome + "|", True, COR_TEXTO)
        tela.blit(input_box, ((tela.get_width()-input_box.get_width())//2, tela.get_height()//2))
        
        pygame.display.flip()
    
    return nome.strip()

def carregar_rankings():
    try:
        with open(RANKING_FILE, 'r') as f:
            linhas = f.readlines()
            rankings = {'Fácil': [], 'Médio': [], 'Difícil': []}
            
            for linha in linhas:
                partes = linha.strip().split(';')
                if len(partes) == 4:
                    nome, pontos, dificuldade, data = partes
                    rankings[dificuldade].append((nome, int(pontos), data))
            
            # Ordenar cada categoria individualmente
            for dificuldade in rankings:
                rankings[dificuldade].sort(key=lambda x: (-x[1], x[2]))
                rankings[dificuldade] = rankings[dificuldade][:10]  # Top 10 por dificuldade
            
            return rankings
    
    except FileNotFoundError:
        return {'Fácil': [], 'Médio': [], 'Difícil': []}
def salvar_pontuacao(nome, pontos, dificuldade):
    # Verificar se o jogador já existe no ranking com a mesma pontuação e dificuldade
    try:
        with open(RANKING_FILE, 'r') as f:
            linhas = f.readlines()
            # Verificar se já existe uma entrada para o jogador com a mesma pontuação e dificuldade
            for linha in linhas:
                partes = linha.strip().split(';')
                if len(partes) == 4:
                    nome_existente, pontos_existentes, dificuldade_existente, _ = partes
                    if nome_existente == nome and int(pontos_existentes) == pontos and dificuldade_existente == dificuldade:
                        return  # Não salva novamente, já existe uma entrada
    except FileNotFoundError:
        # Caso o arquivo não exista ainda, nada a fazer
        pass

    # Se não encontrou uma entrada duplicada, salva a pontuação
    data = datetime.now().strftime("%d/%m/%Y %H:%M")
    with open(RANKING_FILE, 'a') as f:
        f.write(f"{nome};{pontos};{dificuldade};{data}\n")

    # Limitar o número de entradas no ranking (top 10)
    rankings = carregar_rankings()  # Carrega o ranking atual
    if dificuldade in rankings:
        rankings[dificuldade] = sorted(rankings[dificuldade], key=lambda x: (-x[1], x[2]))[:10]  # Ordena e mantém apenas os 10 melhores

    # Reescrever o arquivo com os rankings limitados
    with open(RANKING_FILE, 'w') as f:
        for dificuldade, jogadores in rankings.items():
            for jogador in jogadores:
                nome, pontos, data = jogador
                f.write(f"{nome};{pontos};{dificuldade};{data}\n")



# Seleção de dificuldade centralizada
def selecionar_dificuldade(tela):
    fonte = pygame.font.SysFont(None, 36)
    fonte_titulo = pygame.font.SysFont(None, 48)  # Fonte maior para o título
    
    itens = list(DIFICULDADES.items())
    total = len(itens)
    btn_w, btn_h, gap = 400, 80, 30
    
    # Centralização vertical
    total_h = total*btn_h + (total-1)*gap
    start_y = (tela.get_height() - total_h) // 2
    
    # Centralização horizontal
    btn_x = (tela.get_width() - btn_w) // 2
    
    botoes = []
    for idx, (nome, pares, _) in itens:
        y = start_y + list(DIFICULDADES).index(idx)*(btn_h + gap)
        rect = pygame.Rect(btn_x, y, btn_w, btn_h)
        botoes.append((idx, nome, pares, rect))
    
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                for idx, _, _, rect in botoes:
                    if rect.collidepoint(ev.pos):
                        return idx
        
        tela.fill(COR_FUNDO)
        
        # Título centralizado
        title = fonte_titulo.render("Selecione a Dificuldade", True, COR_TEXTO)
        titulo_x = (tela.get_width() - title.get_width()) // 2
        tela.blit(title, (titulo_x, start_y - 80))  # Mais espaço acima dos botões
        
        # Botões e texto centralizados
        for _, nome, pares, rect in botoes:
            pygame.draw.rect(tela, COR_BOTAO, rect)
            
            # Texto centralizado dentro do botão
            texto = f"{nome}"
            txt = fonte.render(texto, True, COR_TEXTO)
            
            # Centralizar texto no botão
            txt_x = rect.x + (btn_w - txt.get_width()) // 2
            txt_y = rect.y + (btn_h - txt.get_height()) // 2
            tela.blit(txt, (txt_x, txt_y))
        
        pygame.display.flip()
class Jogo:
    def __init__(self, tela, nome_jogador, dificuldade, notificacoes):
        self.tela = tela
        self.nome_jogador = nome_jogador
        self.dificuldade = dificuldade
        self.pontuacao_acumulada = 0  # Inicializa a pontuação acumulada
        self.notificacoes = notificacoes  # Instância de Notificação

    def acumular_pontos(self, pontos):
        """Acumula pontos durante o jogo"""
        self.pontuacao_acumulada += pontos

    def finalizar_jogo(self):
        """Salva a pontuação final quando o jogo terminar"""
        salvar_pontuacao(self.nome_jogador, self.pontuacao_acumulada, self.dificuldade)

    def executar_notificacao(self, pontos):
        """Dispara a notificação e acumula os pontos"""
        self.notificacoes.disparar_notificacao(pontos)
        self.acumular_pontos(pontos)  # Acumula os pontos

def iniciar_jogo(tela, diff_id, nome_jogador):
    notificacoes = Notificacao()  # Criação da instância de Notificação
    _, pares, pesos = DIFICULDADES[diff_id]
    regioes = list(pesos.keys())
    pesos_list = [pesos[r] for r in regioes]
    escolhidos = []

    # Seleção dos times
    while len(escolhidos) < pares:
        reg = random.choices(regioes, weights=pesos_list, k=1)[0]
        tids = get_time_ids(reg)
        if not tids:
            raise RuntimeError(f"Nenhum time válido para região {reg}")
        time_id = random.choice(tids)
        if (reg, time_id) not in escolhidos:
            escolhidos.append((reg, time_id))
    if not hasattr(notificacoes, 'som_notificacao') or notificacoes.som_notificacao is None:
        print("AVISO: Som de notificação não foi carregado corretamente!")
        print("Verifique se o arquivo existe em:", os.path.join(SONS_PATH, 'notificacao.wav'))
    # Criação do deck
    deck = []
    for reg, time_id in escolhidos:
        deck.append((reg, time_id, 0))
        deck.append((reg, time_id, 1))
    random.shuffle(deck)

    if diff_id == 0:    # Fácil
        cols = 5
    elif diff_id == 1:  # Médio
        cols = 6
    else:               # Difícil
        cols = 7

    rows = math.ceil(len(deck) / cols)
    cell_padding = 20  # Espaço entre as cartas
    max_card_width = tela.get_width() // cols - cell_padding
    max_card_height = tela.get_height() // rows - cell_padding

    # Centralizando o grid na tela
    total_grid_width = cols * max_card_width + (cols - 1) * cell_padding
    start_x = (tela.get_width() - total_grid_width) // 2

    cartas = []
    for i, (reg, time_id, tipo) in enumerate(deck):
        r, c = divmod(i, cols)
        # Calcular posição com padding
        x = start_x + c * (max_card_width + cell_padding)
        y = r * (max_card_height + cell_padding)
        cell = pygame.Rect(x, y, max_card_width, max_card_height)
        carta = Carta(reg, time_id, tipo)
        carta.set_rect_and_scale(cell)
        cartas.append(carta)

    # Criando instância da classe Jogo e passando a instância de notificações
    jogo = Jogo(tela, nome_jogador, DIFICULDADES[diff_id][0], notificacoes)

    # Variáveis do jogo
    selecionadas = []
    clock = pygame.time.Clock()
    fonte = pygame.font.SysFont(None, 48)
    comparando = False
    tempo_virada = 0
    inicio_jogo = pygame.time.get_ticks()
    jogo_ativo = True
    # Loop principal do jogo
    while jogo_ativo:
        tempo_atual = pygame.time.get_ticks()
        tempo_decorrido = tempo_atual - inicio_jogo
        tempo_restante = max(TEMPO_JOGO - tempo_decorrido, 0)
        mouse_pos = pygame.mouse.get_pos()

        # Eventos
        for ev in pygame.event.get():
            if ev.type == pl.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pl.MOUSEBUTTONDOWN and not comparando:
                for c in cartas:
                    if c.rect.collidepoint(ev.pos) and not c.face_up and not c.matched:
                        c.flip()
                        selecionadas.append(c)
                        if len(selecionadas) == 2:
                            comparando = True
                            tempo_virada = pygame.time.get_ticks()

        # Verificação de tempo
        if tempo_restante <= 0 or all(c.matched for c in cartas):
            jogo_ativo = False

        # Atualização da tela
        tela.fill(COR_FUNDO)
        for c in cartas:
            c.draw(tela, mouse_pos)

        # Lógica de comparação
        if comparando and (pygame.time.get_ticks() - tempo_virada) > FLIP_DELAY:
            a, b = selecionadas
            if (a.regiao_id, a.time_id) == (b.regiao_id, b.time_id):
                a.matched = b.matched = True 
                pontos_ganhos = SCORE_MATRIX[diff_id][a.regiao_id]
                jogo.executar_notificacao(pontos_ganhos)
            else:   
                a.flip()
                b.flip()
            selecionadas.clear()
            comparando = False

        # Atualizar notificações
        notificacoes.update()

        # Textos
        textp = fonte.render(f"Pontos: {jogo.pontuacao_acumulada}", True, COR_TEXTO)  # Mostra a pontuação acumulada
        tela.blit(textp, (20, 20))
        texto_tempo = fonte.render(f"Tempo: {tempo_restante//1000}s", True, COR_TEXTO)
        tela.blit(texto_tempo, (tela.get_width()-200, 20))
        notificacoes.draw(tela)
        
        pygame.display.flip()
        clock.tick(60)

    # Ao fim do jogo, salvar pontuação
    jogo.finalizar_jogo()
    
    # Mostrar tela de game over
    if tela_game_over(tela, jogo.pontuacao_acumulada, tempo_restante <= 0):
        return 

    textp = fonte.render(f"Pontos: {jogo.pontuacao_acumulada}", True, COR_TEXTO)  # Mostra a pontuação final
    tela.blit(textp, (20, 20))
    pygame.display.flip()
    clock.tick(60)
def tela_game_over(tela, pontos, tempo_esgotado):
    fonte = pygame.font.SysFont(None, 48)
    btn_menu = pygame.image.load(os.path.join('assets', 'images', 'button_menu.png'))
    btn_menu_rect = btn_menu.get_rect(center=(tela.get_width()//2, tela.get_height()//2 + 100))
    
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN and btn_menu_rect.collidepoint(ev.pos):
                return True  
        
        tela.fill(COR_FUNDO)
        
        if tempo_esgotado:
            texto = fonte.render("Tempo Esgotado!", True, (255, 0, 0))
        else:
            texto = fonte.render("Parabéns! Você completou o jogo!", True, (0, 150, 0))
        
        tela.blit(texto, ((tela.get_width()-texto.get_width())//2, tela.get_height()//2 - 150))
        texto_pontos = fonte.render(f"Pontuação final: {pontos}", True, COR_TEXTO)
        tela.blit(texto_pontos, ((tela.get_width()-texto_pontos.get_width())//2, tela.get_height()//2-110))
        tela.blit(btn_menu, btn_menu_rect)
        
        pygame.display.flip()
if __name__ == '__main__':
    tela = init_pygame()
    
    while True:
        acao = tela_inicial(tela)
        
        if acao == 'ranking':
            tela_ranking(tela)
        elif acao == 'play':
            nome = input_nome(tela)
            diff = selecionar_dificuldade(tela)
            iniciar_jogo(tela, diff, nome)
