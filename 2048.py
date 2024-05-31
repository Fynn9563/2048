import pygame
import random
import sys
import copy
import threading

# Initialize Pygame
pygame.init()

# Constants
SIZE = 4
TILE_SIZE = 100
MARGIN = 10
BUTTON_HEIGHT = 50
INPUT_HEIGHT = 50
WIDTH = HEIGHT = SIZE * (TILE_SIZE + MARGIN) + MARGIN
SCREEN_HEIGHT = HEIGHT + BUTTON_HEIGHT * 3 + INPUT_HEIGHT
BACKGROUND_COLOR = (187, 173, 160)
BUTTON_COLOR = (119, 110, 101)
BUTTON_TEXT_COLOR = (255, 255, 255)
TILE_COLORS = {
    0: (205, 193, 180),
    2: (238, 228, 218),
    4: (237, 224, 200),
    8: (242, 177, 121),
    16: (245, 149, 99),
    32: (246, 124, 95),
    64: (246, 94, 59),
    128: (237, 207, 114),
    256: (237, 204, 97),
    512: (237, 200, 80),
    1024: (237, 197, 63),
    2048: (237, 194, 46),
}
FONT = pygame.font.Font(None, 50)
BUTTON_FONT = pygame.font.Font(None, 40)

# Initialize the game screen
screen = pygame.display.set_mode((WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("2048")

selected_tile = None
valid_numbers = {0, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 4096, 8192, 16384, 32768, 65536, 131072}
autoplay = False
input_value = ""
key_pressed = False

# AI Constants
GoalType = {'UNDEFINED': -1, 'BUILD': 0, 'SHIFT': 1, 'MOVE': 2}

class Goal:
    def __init__(self):
        self.type = GoalType['UNDEFINED']

class SmartAI:
    def __init__(self, game):
        self.game = game

    def next_move(self):
        original_quality = self.grid_quality(self.game.board)
        results = self.plan_ahead(self.game.board, 3, original_quality)
        best_result = self.choose_best_move(results, original_quality)
        return best_result['direction']

    def plan_ahead(self, board, num_moves, original_quality):
        results = [None] * 4
        for d in range(4):
            test_board = copy.deepcopy(board)
            moved = self.move(test_board, d)
            if not moved:
                results[d] = None
                continue
            result = {'quality': -1, 'probability': 1, 'quality_loss': 0, 'direction': d}
            available_cells = self.available_cells(test_board)
            for cell in available_cells:
                has_adjacent_tile = False
                for d2 in range(4):
                    adj_cell = (cell[0] + self.get_vector(d2)[0], cell[1] + self.get_vector(d2)[1])
                    if self.cell_content(test_board, adj_cell):
                        has_adjacent_tile = True
                        break
                if not has_adjacent_tile:
                    continue
                test_board2 = copy.deepcopy(test_board)
                self.add_tile(test_board2, cell, 2)
                if num_moves > 1:
                    sub_results = self.plan_ahead(test_board2, num_moves - 1, original_quality)
                    tile_result = self.choose_best_move(sub_results, original_quality)
                else:
                    tile_quality = self.grid_quality(test_board2)
                    tile_result = {'quality': tile_quality, 'probability': 1, 'quality_loss': max(original_quality - tile_quality, 0)}
                if result['quality'] == -1 or tile_result['quality'] < result['quality']:
                    result['quality'] = tile_result['quality']
                    result['probability'] = tile_result['probability'] / len(available_cells)
                elif tile_result['quality'] == result['quality']:
                    result['probability'] += tile_result['probability'] / len(available_cells)
                result['quality_loss'] += tile_result['quality_loss'] / len(available_cells)
            results[d] = result
        return results

    def choose_best_move(self, results, original_quality):
        best_result = None
        for result in results:
            if result is None:
                continue
            if (not best_result or
                result['quality_loss'] < best_result['quality_loss'] or
                (result['quality_loss'] == best_result['quality_loss'] and result['quality'] > best_result['quality']) or
                (result['quality_loss'] == best_result['quality_loss'] and result['quality'] == best_result['quality'] and result['probability'] < best_result['probability'])):
                best_result = result
        if not best_result:
            best_result = {'quality': -1, 'probability': 1, 'quality_loss': original_quality, 'direction': 0}
        return best_result

    def grid_quality(self, board):
        mono_score = 0
        traversals = self.build_traversals(SIZE)
        for i in range(SIZE):
            inc_score = dec_score = prev_value = -1
            for j in range(SIZE):
                tile_value = board[traversals[i][j][0]][traversals[i][j][1]]
                if tile_value <= prev_value or prev_value == -1:
                    dec_score += tile_value
                    if tile_value < prev_value:
                        inc_score -= prev_value
                inc_score += tile_value
                prev_value = tile_value
            mono_score += max(inc_score, dec_score)
        empty_score = len(self.available_cells(board)) * 8
        return mono_score + empty_score

    def available_cells(self, board):
        return [(r, c) for r in range(SIZE) for c in range(SIZE) if board[r][c] == 0]

    def cell_content(self, board, cell):
        r, c = cell
        if 0 <= r < SIZE and 0 <= c < SIZE:
            return board[r][c] != 0
        return False

    def get_vector(self, direction):
        return [(0, -1), (1, 0), (0, 1), (-1, 0)][direction]

    def move(self, board, direction):
        moved = False
        if direction == 0:
            moved = move_up(board)
        elif direction == 1:
            moved = move_right(board)
        elif direction == 2:
            moved = move_down(board)
        elif direction == 3:
            moved = move_left(board)
        return moved

    def add_tile(self, board, cell, value):
        board[cell[0]][cell[1]] = value

    def build_traversals(self, size):
        return [[(r, c) for r in range(size)] for c in range(size)]

def init_game():
    board = [[0] * SIZE for _ in range(SIZE)]
    add_new_tile(board)
    add_new_tile(board)
    return board

def add_new_tile(board):
    empty_tiles = [(r, c) for r in range(SIZE) for c in range(SIZE) if board[r][c] == 0]
    if not empty_tiles:
        return
    r, c = random.choice(empty_tiles)
    board[r][c] = 2 if random.random() < 0.9 else 4

def draw_board(board, best_move, score, game_over):
    screen.fill(BACKGROUND_COLOR)
    for r in range(SIZE):
        for c in range(SIZE):
            value = board[r][c]
            color = TILE_COLORS.get(value, TILE_COLORS[2048])
            rect = pygame.Rect(c * (TILE_SIZE + MARGIN) + MARGIN, r * (TILE_SIZE + MARGIN) + MARGIN + INPUT_HEIGHT, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, color, rect)
            if value != 0:
                text = FONT.render(str(value), True, (119, 110, 101))
                text_rect = text.get_rect(center=rect.center)
                screen.blit(text, text_rect)
            if selected_tile == (r, c):
                pygame.draw.rect(screen, (255, 0, 0), rect, 3)
    
    draw_input_box()
    draw_hint(best_move)
    draw_score(score)
    draw_autoplay_button()
    if game_over:
        draw_game_over()
    pygame.display.update()

def draw_input_box():
    global input_value
    pygame.draw.rect(screen, (255, 255, 255), (MARGIN, MARGIN, WIDTH - 2 * MARGIN, INPUT_HEIGHT - MARGIN))
    font = pygame.font.Font(None, 36)
    text_surface = font.render(input_value, True, (0, 0, 0))
    screen.blit(text_surface, (MARGIN + 5, MARGIN + 5))

def draw_hint(best_move):
    best_move_text = ["Up", "Right", "Down", "Left"]
    hint_text = BUTTON_FONT.render(f"Best Move: {best_move_text[best_move]}", True, BUTTON_TEXT_COLOR)
    hint_text_rect = hint_text.get_rect(center=(WIDTH // 2, HEIGHT + BUTTON_HEIGHT // 2 + INPUT_HEIGHT))
    pygame.draw.rect(screen, BUTTON_COLOR, pygame.Rect(0, HEIGHT + INPUT_HEIGHT, WIDTH, BUTTON_HEIGHT))
    screen.blit(hint_text, hint_text_rect)

def draw_score(score):
    score_text = BUTTON_FONT.render(f"Score: {score}", True, BUTTON_TEXT_COLOR)
    score_text_rect = score_text.get_rect(center=(WIDTH // 2, HEIGHT + BUTTON_HEIGHT + BUTTON_HEIGHT // 2 + INPUT_HEIGHT))
    pygame.draw.rect(screen, BUTTON_COLOR, pygame.Rect(0, HEIGHT + BUTTON_HEIGHT + INPUT_HEIGHT, WIDTH, BUTTON_HEIGHT))
    screen.blit(score_text, score_text_rect)

def draw_game_over():
    game_over_text = BUTTON_FONT.render("Game Over!", True, BUTTON_TEXT_COLOR)
    game_over_text_rect = game_over_text.get_rect(center=(WIDTH // 2, HEIGHT + BUTTON_HEIGHT // 2 + INPUT_HEIGHT))
    pygame.draw.rect(screen, BUTTON_COLOR, pygame.Rect(0, HEIGHT + INPUT_HEIGHT, WIDTH, BUTTON_HEIGHT))
    screen.blit(game_over_text, game_over_text_rect)

def draw_autoplay_button():
    button_text = "Autoplay" if not autoplay else "Stop"
    autoplay_button = BUTTON_FONT.render(button_text, True, BUTTON_TEXT_COLOR)
    autoplay_button_rect = autoplay_button.get_rect(center=(WIDTH // 2, HEIGHT + BUTTON_HEIGHT * 2.5 + INPUT_HEIGHT))
    pygame.draw.rect(screen, BUTTON_COLOR, pygame.Rect(0, HEIGHT + BUTTON_HEIGHT * 2 + INPUT_HEIGHT, WIDTH, BUTTON_HEIGHT))
    screen.blit(autoplay_button, autoplay_button_rect)

def merge_left(row):
    merged = [v for v in row if v != 0]
    for i in range(1, len(merged)):
        if merged[i] == merged[i - 1]:
            merged[i - 1] *= 2
            merged[i] = 0
    merged = [v for v in merged if v != 0]
    return merged + [0] * (SIZE - len(merged))

def rotate_board_clockwise(board):
    return [[board[SIZE - c - 1][r] for c in range(SIZE)] for r in range(SIZE)]

def rotate_board_counterclockwise(board):
    return [[board[c][SIZE - r - 1] for c in range(SIZE)] for r in range(SIZE)]

def move_left(board):
    moved = False
    for r in range(SIZE):
        new_row = merge_left(board[r])
        if new_row != board[r]:
            board[r] = new_row
            moved = True
    return moved

def move_right(board):
    moved = False
    for r in range(SIZE):
        new_row = merge_left(board[r][::-1])[::-1]
        if new_row != board[r]:
            board[r] = new_row
            moved = True
    return moved

def move_up(board):
    moved = False
    rotated = rotate_board_counterclockwise(board)
    moved = move_left(rotated)
    if moved:
        board[:] = rotate_board_clockwise(rotated)
    return moved

def move_down(board):
    moved = False
    rotated = rotate_board_clockwise(board)
    moved = move_left(rotated)
    if moved:
        board[:] = rotate_board_counterclockwise(rotated)
    return moved

def evaluate_board(board):
    empty_tiles = sum(row.count(0) for row in board)
    max_tile = max(max(row) for row in board)
    corner_value = max(board[0][0], board[0][SIZE-1], board[SIZE-1][0], board[SIZE-1][SIZE-1])
    return empty_tiles * 100 + max_tile + corner_value * 2

def get_best_move(board, runs=100):
    ai = SmartAI(game)
    return ai.next_move()

def check_game_over(board):
    for r in range(SIZE):
        for c in range(SIZE):
            if board[r][c] == 0:
                return False
            if r < SIZE - 1 and board[r][c] == board[r + 1][c]:
                return False
            if c < SIZE - 1 and board[r][c] == board[r][c + 1]:
                return False
    return True

def calculate_score(board):
    return sum(sum(row) for row in board)

def autoplay_game(board):
    global autoplay
    while autoplay and not check_game_over(board):
        best_move = get_best_move(board)
        move_made = False
        if best_move == 0:
            move_made = move_up(board)
        elif best_move == 1:
            move_made = move_right(board)
        elif best_move == 2:
            move_made = move_down(board)
        elif best_move == 3:
            move_made = move_left(board)
        if move_made:
            add_new_tile(board)
        best_move = get_best_move(board)
        score = calculate_score(board)
        game_over = check_game_over(board)
        draw_board(board, best_move, score, game_over)
        pygame.time.delay(100)

def main():
    global selected_tile, autoplay, game, input_value, key_pressed
    game = GameController(init_game())
    best_move = get_best_move(game.board)
    score = calculate_score(game.board)
    game_over = check_game_over(game.board)
    draw_board(game.board, best_move, score, game_over)

    while True:
        move_made = False
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYUP:
                key_pressed = False

            elif event.type == pygame.KEYDOWN:
                if not key_pressed:
                    key_pressed = True
                    if event.key == pygame.K_RETURN and selected_tile:
                        if input_value.isdigit() and int(input_value) in valid_numbers:
                            r, c = selected_tile
                            game.board[r][c] = int(input_value)
                            input_value = ""
                            selected_tile = None
                            move_made = True
                    elif event.key == pygame.K_BACKSPACE:
                        input_value = input_value[:-1]
                    elif event.unicode.isdigit():
                        input_value += event.unicode
                    elif event.key == pygame.K_LEFT:
                        move_made = move_left(game.board)
                    elif event.key == pygame.K_RIGHT:
                        move_made = move_right(game.board)
                    elif event.key == pygame.K_UP:
                        move_made = move_up(game.board)
                    elif event.key == pygame.K_DOWN:
                        move_made = move_down(game.board)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if INPUT_HEIGHT <= y < HEIGHT + INPUT_HEIGHT:
                    selected_tile = ((y - MARGIN - INPUT_HEIGHT) // (TILE_SIZE + MARGIN), (x - MARGIN) // (TILE_SIZE + MARGIN))
                elif HEIGHT + BUTTON_HEIGHT * 2 + INPUT_HEIGHT < y < HEIGHT + BUTTON_HEIGHT * 3 + INPUT_HEIGHT:
                    autoplay = not autoplay
                    if autoplay:
                        threading.Thread(target=autoplay_game, args=(game.board,)).start()

        if not autoplay and move_made:
            add_new_tile(game.board)
            input_value = ""
            selected_tile = None

        best_move = get_best_move(game.board)
        score = calculate_score(game.board)
        game_over = check_game_over(game.board)
        draw_board(game.board, best_move, score, game_over)
        if move_made:
            print(f"Best move is: {best_move}")  # Debug statement to print the best move

class GameController:
    def __init__(self, board):
        self.board = board

if __name__ == "__main__":
    main()
