from collections import defaultdict
from urllib.parse import urlencode
import os
import re
import ast

import chess
import yaml

with open('data/settings.yaml', 'r') as settings_file:
    settings = yaml.load(settings_file, Loader=yaml.FullLoader)


def create_link(text, link):
    return f"[{text}]({link})"

def create_issue_link(source, dest_list):
    issue_link = settings['issues']['link'].format(
        repo=os.environ["GITHUB_REPOSITORY"],
        params=urlencode(settings['issues']['move'], safe="{}"))

    ret = [create_link(dest, issue_link.format(source=source, dest=dest)) for dest in sorted(dest_list)]
    return ", ".join(ret)

def generate_top_moves():
    # Verifica se o arquivo existe, se não existir, cria com um dicionário vazio
    if not os.path.exists("data/top_moves.txt"):
        with open("data/top_moves.txt", 'w') as file:
            file.write("{}")
    
    with open("data/top_moves.txt", 'r') as file:
        contents = file.read()
        # Se o arquivo estiver vazio, usa dicionário vazio
        if not contents.strip():
            dictionary = {}
        else:
            dictionary = ast.literal_eval(contents)

    markdown = "\n"
    markdown += "| Total moves |  User  |\n"
    markdown += "| :---------: | :----- |\n"

    max_entries = settings['misc']['max_top_moves']
    for key,val in sorted(dictionary.items(), key=lambda x: x[1], reverse=True)[:max_entries]:
        markdown += "| {} | {} |\n".format(val, create_link(key, "https://github.com/" + key[1:]))

    return markdown + "\n"

def get_algebraic_notation():
    """
    Extrai a notação algébrica das últimas jogadas do arquivo PGN
    Retorna uma lista com as últimas N jogadas no formato: "5. c4", "5... e5", etc.
    """
    if not os.path.exists('games/current.pgn'):
        return []
    
    try:
        with open('games/current.pgn') as pgn_file:
            game = chess.pgn.read_game(pgn_file)
            if game is None:
                return []
            
            # Extrair notação principal
            board = game.board()
            moves = []
            
            # Pular cabeçalhos do PGN
            node = game
            move_number = 1
            
            while node.variations:
                next_node = node.variations[0]
                move = next_node.move
                
                # Obter notação algébrica
                san = board.san(move)
                
                # Determinar se é movimento das brancas ou pretas
                if board.turn == chess.WHITE:  # Antes de fazer o movimento, turn = WHITE significa que é movimento das brancas
                    moves.append(f"{move_number}. {san}")
                else:
                    moves.append(f"{move_number}... {san}")
                    move_number += 1
                
                board.push(move)
                node = next_node
            
            return moves  # Retorna todas as jogadas
            
    except Exception as e:
        print(f"Erro ao ler notação algébrica: {e}")
        return []

def generate_last_moves():
    if not os.path.exists("data/last_moves.txt"):
        return "\n| Move | Algebraic Notation | Author |\n| :--: | :----------------: | :----- |\n| *Nenhum movimento ainda* | | |\n\n"
    
    # Pegar notação algébrica do PGN
    algebraic_moves = get_algebraic_notation()
    
    markdown = "\n"
    markdown += "| Move | Algebraic Notation | Author |\n"
    markdown += "| :--: | :----------------: | :----- |\n"

    # Ler todas as linhas do arquivo last_moves.txt
    with open("data/last_moves.txt", 'r') as file:
        lines = file.readlines()
    
    # Filtrar apenas as jogadas (ignorar Start game)
    jogadas = []
    for line in lines:
        if "Start game" not in line:
            jogadas.append(line.strip())
    
    # Pegar as últimas N jogadas (as mais recentes)
    max_moves = settings['misc']['max_last_moves']
    ultimas_jogadas = jogadas[-max_moves:]
    
    # AGORA A CORREÇÃO: Vamos criar duas listas separadas
    jogadas_para_mostrar = []
    notacoes_para_mostrar = []
    
    # Pegar as últimas N notações (na ordem do PGN)
    ultimas_notacoes = algebraic_moves[-len(ultimas_jogadas):]
    
    # Inverter a ordem das jogadas (para mostrar mais recente primeiro)
    jogadas_invertidas = list(reversed(ultimas_jogadas))
    
    # Manter as notações na ordem original (já estão corretas)
    notacoes_ordem_original = ultimas_notacoes
    
    # Mostrar lado a lado
    for i in range(len(jogadas_invertidas)):
        jogada = jogadas_invertidas[i]
        notacao = notacoes_ordem_original[i]
        
        if ":" not in jogada:
            continue
            
        parts = jogada.split(':')
        move_code = parts[0].strip()
        author = parts[1].strip()
        
        # Formatar movimento
        match_obj = re.search('([A-H][1-8])([A-H][1-8])', move_code, re.I)
        if match_obj:
            source = match_obj.group(1).upper()
            dest = match_obj.group(2).upper()
            move_display = f"`{source} to {dest}`"
        else:
            move_display = f"`{move_code}`"
        
        markdown += f"| {move_display} | `{notacao}` | {create_link(author, 'https://github.com/' + author[1:])} |\n"
    
    return markdown + "\n"

def generate_moves_list(board):
    # Create dictionary and fill it
    moves_dict = defaultdict(set)

    for move in board.legal_moves:
        source = chess.SQUARE_NAMES[move.from_square].upper()
        dest   = chess.SQUARE_NAMES[move.to_square].upper()

        moves_dict[source].add(dest)

    # Write everything in Markdown format
    markdown = ""

    if board.is_game_over():
        issue_link = settings['issues']['link'].format(
            repo=os.environ["GITHUB_REPOSITORY"],
            params=urlencode(settings['issues']['new_game']))

        return "**GAME IS OVER!** " + create_link("Click here", issue_link) + " to start a new game :D\n"

    if board.is_check():
        markdown += "**CHECK!** Choose your move wisely!\n"

    markdown += "|  FROM  | TO (Just click a link!) |\n"
    markdown += "| :----: | :---------------------- |\n"

    for source,dest in sorted(moves_dict.items()):
        markdown += "| **" + source + "** | " + create_issue_link(source, dest) + " |\n"

    return markdown

def get_captured_pieces(board):
    """
    Retorna um dicionário com as peças capturadas de cada cor
    """
    # Configuração inicial das peças
    initial_pieces = {
        chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2,
        chess.ROOK: 2, chess.QUEEN: 1, chess.KING: 1
    }
    
    # Contar peças atuais no tabuleiro
    current_pieces = {chess.WHITE: defaultdict(int), chess.BLACK: defaultdict(int)}
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            current_pieces[piece.color][piece.piece_type] += 1
    
    # Mapeamento de peças para SVGs
    piece_to_svg = {
        (chess.BLACK, chess.PAWN): "img/black/pawn.svg",
        (chess.BLACK, chess.KNIGHT): "img/black/knight.svg",
        (chess.BLACK, chess.BISHOP): "img/black/bishop.svg",
        (chess.BLACK, chess.ROOK): "img/black/rook.svg",
        (chess.BLACK, chess.QUEEN): "img/black/queen.svg",
        (chess.BLACK, chess.KING): "img/black/king.svg",
        (chess.WHITE, chess.PAWN): "img/white/pawn.svg",
        (chess.WHITE, chess.KNIGHT): "img/white/knight.svg",
        (chess.WHITE, chess.BISHOP): "img/white/bishop.svg",
        (chess.WHITE, chess.ROOK): "img/white/rook.svg",
        (chess.WHITE, chess.QUEEN): "img/white/queen.svg",
        (chess.WHITE, chess.KING): "img/white/king.svg",
    }
    
    # Calcular peças capturadas
    captured = {
        'white_captured': [],  # Peças que as BRANCAS capturaram (portanto, são peças PRETAS)
        'black_captured': []   # Peças que as PRETAS capturaram (portanto, são peças BRANCAS)
    }
    
    # DEBUG: Vamos imprimir para ver o que está acontecendo
    print(f"DEBUG - Current pieces WHITE: {dict(current_pieces[chess.WHITE])}")
    print(f"DEBUG - Current pieces BLACK: {dict(current_pieces[chess.BLACK])}")
    
    # Peças capturadas pelas BRANCAS (peças PRETAS que faltam)
    for piece_type, initial_count in initial_pieces.items():
        if piece_type != chess.KING:  # Rei nunca é capturado
            current_count = current_pieces[chess.BLACK].get(piece_type, 0)
            captured_count = initial_count - current_count
            print(f"DEBUG - Black {chess.piece_name(piece_type)}: initial={initial_count}, current={current_count}, captured={captured_count}")
            for _ in range(captured_count):
                captured['white_captured'].append(piece_to_svg[(chess.BLACK, piece_type)])
    
    # Peças capturadas pelas PRETAS (peças BRANCAS que faltam)
    for piece_type, initial_count in initial_pieces.items():
        if piece_type != chess.KING:
            current_count = current_pieces[chess.WHITE].get(piece_type, 0)
            captured_count = initial_count - current_count
            print(f"DEBUG - White {chess.piece_name(piece_type)}: initial={initial_count}, current={current_count}, captured={captured_count}")
            for _ in range(captured_count):
                captured['black_captured'].append(piece_to_svg[(chess.WHITE, piece_type)])
    
    print(f"DEBUG - white_captured (peças pretas capturadas pelas brancas): {len(captured['white_captured'])} peças")
    print(f"DEBUG - black_captured (peças brancas capturadas pelas pretas): {len(captured['black_captured'])} peças")
    
    return captured

def captured_pieces_to_markdown(board):
    """
    Gera o HTML para exibir as peças capturadas ao lado do tabuleiro
    """
    captured = get_captured_pieces(board)
    
    markdown = '\n<div align="center">\n\n'
    markdown += '### ⚔️ Peças Capturadas\n\n'
    
    # Peças capturadas pelas pretas (lado esquerdo - visão das pretas)
    markdown += '<table>\n'
    markdown += '  <tr>\n'
    markdown += '    <td width="200" align="center"><strong>⚫ Pretas capturaram</strong><br>'
    for svg_path in captured['black_captured']:
        markdown += f'<img src="{svg_path}" width=30px> '
        
    markdown += '\n    </td>\n'
    
    # Peças capturadas pelas brancas (lado direito - visão das brancas)
    markdown += '    <td valign="middle" align="center" width="100">\n'
    markdown += '      <strong>⚪ Brancas capturaram</strong><br>\n'
    
    # Adicionar as imagens das peças capturadas pelas brancas
    if captured['white_captured']:
        for svg_path in captured['white_captured']:
            markdown += f'      <img src="{svg_path}" width=35px><br>\n'
    else:
        markdown += '      <em>nenhuma</em>\n'
    
    markdown += '    </td>\n'  # Fechamento correto da tag <td>
    
    markdown += '  </tr>\n'
    markdown += '</table>\n'

    return markdown

def board_to_markdown(board):
    board_list = [[item for item in line.split(' ')] for line in str(board).split('\n')]
    markdown = ""

    images = {
        "r": "img/black/rook.svg", "n": "img/black/knight.svg", "b": "img/black/bishop.svg",
        "q": "img/black/queen.svg", "k": "img/black/king.svg", "p": "img/black/pawn.svg",
        "R": "img/white/rook.svg", "N": "img/white/knight.svg", "B": "img/white/bishop.svg",
        "Q": "img/white/queen.svg", "K": "img/white/king.svg", "P": "img/white/pawn.svg",
        ".": "img/blank.png"
    }

    # Get captured pieces
    captured = get_captured_pieces(board)
    
    # TABULEIRO (Markdown puro - sem tabela HTML)
    if board.turn == chess.BLACK:
        markdown += "|   | H | G | F | E | D | C | B | A |   |\n"
    else:
        markdown += "|   | A | B | C | D | E | F | G | H |   |\n"
    markdown += "|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|\n"

    rows = range(1, 9)
    if board.turn == chess.BLACK:
        rows = reversed(rows)

    for row in rows:
        markdown += "| **" + str(9 - row) + "** | "
        columns = board_list[row - 1]
        if board.turn == chess.BLACK:
            columns = reversed(columns)
        for elem in columns:
            markdown += "<img src=\"{}\" width=45px> | ".format(images.get(elem, "???"))
        markdown += "**" + str(9 - row) + "** |\n"

    if board.turn == chess.BLACK:
        markdown += "|   | **H** | **G** | **F** | **E** | **D** | **C** | **B** | **A** |   |\n\n"
    else:
        markdown += "|   | **A** | **B** | **C** | **D** | **E** | **F** | **G** | **H** |   |\n\n"
    
    # PEÇAS CAPTURADAS (em linha única abaixo)
    #markdown += "#\n"
    markdown += "### ⚔️ Peças Capturadas\n"
    
    # Brancas capturaram (peças pretas)
    markdown += "**⚪ Brancas:** "
    if captured['white_captured']:
        for svg_path in captured['white_captured']:
            markdown += f'<img src="{svg_path}" width=22px> '
    else:
        markdown += "_nenhuma_"
    
    markdown += " &nbsp; | &nbsp; "
    
    # Pretas capturaram (peças brancas)
    markdown += "**⚫ Pretas:** "
    if captured['black_captured']:
        for svg_path in captured['black_captured']:
            markdown += f'<img src="{svg_path}" width=22px> '
    else:
        markdown += "_nenhuma_"
    
    markdown += "\n"

    return markdown
