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
    with open("data/top_moves.txt", 'r') as file:
        dictionary = ast.literal_eval(file.read())

    markdown = "\n"
    markdown += "| Total moves |  User  |\n"
    markdown += "| :---------: | :----- |\n"

    max_entries = settings['misc']['max_top_moves']
    for key,val in sorted(dictionary.items(), key=lambda x: x[1], reverse=True)[:max_entries]:
        markdown += "| {} | {} |\n".format(val, create_link(key, "https://github.com/" + key[1:]))

    return markdown + "\n"

def generate_last_moves():
    markdown = "\n"
    markdown += "| Move | Author |\n"
    markdown += "| :--: | :----- |\n"

    counter = 0

    with open("data/last_moves.txt", 'r') as file:
        for line in file.readlines():
            parts = line.rstrip().split(':')

            if not ":" in line:
                continue

            if counter >= settings['misc']['max_last_moves']:
                break

            counter += 1

            match_obj = re.search('([A-H][1-8])([A-H][1-8])', line, re.I)
            if match_obj is not None:
                source = match_obj.group(1).upper()
                dest   = match_obj.group(2).upper()

                markdown += "| `" + source + "` to `" + dest + "` | " + create_link(parts[1], "https://github.com/" + parts[1].lstrip()[1:]) + " |\n"
            else:
                markdown += "| `" + parts[0] + "` | " + create_link(parts[1], "https://github.com/" + parts[1].lstrip()[1:]) + " |\n"

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
        'white_captured': [],  # Peças pretas capturadas pelas brancas
        'black_captured': []   # Peças brancas capturadas pelas pretas
    }
    
    # Peças capturadas pelas brancas (peças pretas que faltam)
    for piece_type, initial_count in initial_pieces.items():
        if piece_type != chess.KING:
            current_count = current_pieces[chess.BLACK].get(piece_type, 0)
            captured_count = initial_count - current_count
            for _ in range(captured_count):
                captured['white_captured'].append(piece_to_svg[(chess.BLACK, piece_type)])
    
    # Peças capturadas pelas pretas (peças brancas que faltam)
    for piece_type, initial_count in initial_pieces.items():
        if piece_type != chess.KING:
            current_count = current_pieces[chess.WHITE].get(piece_type, 0)
            captured_count = initial_count - current_count
            for _ in range(captured_count):
                captured['black_captured'].append(piece_to_svg[(chess.WHITE, piece_type)])
    
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
    markdown += '</td>\n'
    markdown += '    <td width="400" align="center"><em>(tabuleiro)</em></td>\n'
    markdown += '    <td width="200" align="center"><strong>⚪ Brancas capturaram</strong><br>'
    for svg_path in captured['white_captured']:
        markdown += f'<img src="{svg_path}" width=30px> '
    markdown += '</td>\n'
    markdown += '  </tr>\n'
    markdown += '</table>\n\n'
    markdown += '</div>\n'
    
    return markdown

def board_to_markdown(board):
    board_list = [[item for item in line.split(' ')] for line in str(board).split('\n')]
    markdown = ""

    images = {
        "r": "img/black/rook.svg",
        "n": "img/black/knight.svg",
        "b": "img/black/bishop.svg",
        "q": "img/black/queen.svg",
        "k": "img/black/king.svg",
        "p": "img/black/pawn.svg",

        "R": "img/white/rook.svg",
        "N": "img/white/knight.svg",
        "B": "img/white/bishop.svg",
        "Q": "img/white/queen.svg",
        "K": "img/white/king.svg",
        "P": "img/white/pawn.svg",

        ".": "img/blank.png"
    }

    # Get captured pieces
    captured = get_captured_pieces(board)
    
    # Create a table with captured pieces on the sides
    markdown += '<table>\n'
    markdown += '  <tr>\n'
    
    # Left side - Pieces captured by Black (White pieces that Black took)
    markdown += '    <td valign="middle" align="center" width="100">\n'
    markdown += '      <strong>⚫ Pretas capturaram</strong><br>\n'
    for svg_path in captured['black_captured']:
        markdown += f'      <img src="{svg_path}" width=35px><br>\n'
    markdown += '    </td>\n'
    
    # Center - Chess board
    markdown += '    <td valign="middle">\n\n'
    
    # Write header in Markdown format
    if board.turn == chess.BLACK:
        markdown += "|   | H | G | F | E | D | C | B | A |   |\n"
    else:
        markdown += "|   | A | B | C | D | E | F | G | H |   |\n"
    markdown += "|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|\n"

    # Get Rows
    rows = range(1, 9)
    if board.turn == chess.BLACK:
        rows = reversed(rows)

    # Write board
    for row in rows:
        markdown += "| **" + str(9 - row) + "** | "
        columns = board_list[row - 1]
        if board.turn == chess.BLACK:
            columns = reversed(columns)

        for elem in columns:
            markdown += "<img src=\"{}\" width=50px> | ".format(images.get(elem, "???"))

        markdown += "**" + str(9 - row) + "** |\n"

    # Write footer in Markdown format
    if board.turn == chess.BLACK:
        markdown += "|   | **H** | **G** | **F** | **E** | **D** | **C** | **B** | **A** |   |\n"
    else:
        markdown += "|   | **A** | **B** | **C** | **D** | **E** | **F** | **G** | **H** |   |\n"
    
    markdown += '\n    </td>\n'
    
    # Right side - Pieces captured by White (Black pieces that White took)
    markdown += '    <td valign="middle" align="center" width="100">\n'
    markdown += '      <strong>⚪ Brancas capturaram</strong><br>\n'
    for svg_path in captured['white_captured']:
        markdown += f'      <img src="{svg_path}" width=35px><br>\n'
    markdown += '    </td>\n'
    
    markdown += '  </tr>\n'
    markdown += '</table>\n'

    return markdown
