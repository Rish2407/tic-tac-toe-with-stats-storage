import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from datetime import datetime

# ---------------------- DB LAYER ----------------------
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="tictactoedb"
    )

def create_tables():
    db = connect_db()
    cur = db.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            player_symbol CHAR(1) PRIMARY KEY,
            games_played INT DEFAULT 0,
            wins INT DEFAULT 0,
            losses INT DEFAULT 0,
            draws INT DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS game_history (
            game_id INT AUTO_INCREMENT PRIMARY KEY,
            played_at DATETIME NOT NULL,
            winner VARCHAR(10) NOT NULL,
            board_size INT NOT NULL,
            moves_count INT DEFAULT 0
        )
    """)

    for s in ("X", "O"):
        cur.execute("INSERT IGNORE INTO player_stats (player_symbol) VALUES (%s)", (s,))

    db.commit()
    db.close()

def db_insert_game(winner, board_size, played_at=None, moves_count=0):
    if not played_at or str(played_at).strip() == "":
        played_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db = connect_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO game_history (played_at, winner, board_size, moves_count)
        VALUES (%s, %s, %s, %s)
    """, (played_at, winner, board_size, moves_count))
    db.commit()
    db.close()

def db_fetch_games(order_by="played_at", asc=False):
    allowed = {"game_id","played_at","winner","board_size","moves_count"}
    col = order_by if order_by in allowed else "played_at"
    direction = "ASC" if asc else "DESC"
    db = connect_db()
    cur = db.cursor()
    cur.execute(f"""
        SELECT game_id, played_at, winner, board_size, moves_count
        FROM game_history
        ORDER BY {col} {direction}
    """)
    rows = cur.fetchall()
    db.close()
    return rows

def db_search_games(winner=None, date_from=None, date_to=None, order_by="played_at", asc=False):
    clauses = []
    params  = []
    if winner and winner in ("X","O","Draw"):
        clauses.append("winner = %s")
        params.append(winner)
    if date_from:
        clauses.append("played_at >= %s")
        params.append(date_from + " 00:00:00")
    if date_to:
        clauses.append("played_at <= %s")
        params.append(date_to + " 23:59:59")

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    allowed = {"game_id","played_at","winner","board_size","moves_count"}
    col = order_by if order_by in allowed else "played_at"
    direction = "ASC" if asc else "DESC"

    db = connect_db()
    cur = db.cursor()
    cur.execute(f"""
        SELECT game_id, played_at, winner, board_size, moves_count
        FROM game_history
        {where_sql}
        ORDER BY {col} {direction}
    """, tuple(params))
    rows = cur.fetchall()
    db.close()
    return rows

def db_delete_game(game_id):
    db = connect_db()
    cur = db.cursor()
    cur.execute("DELETE FROM game_history WHERE game_id=%s", (game_id,))
    db.commit()
    db.close()

# ---------------------- GUI HELPERS ----------------------
def populate_tree(tree, rows):
    tree.delete(*tree.get_children())
    for r in rows:
        tree.insert("", tk.END, values=(r[0],
            r[1].strftime("%Y-%m-%d %H:%M:%S") if isinstance(r[1], datetime) else str(r[1]),
            r[2], r[3], r[4]))

# ---------------------- WINDOWS ----------------------
def open_play_window(size):
    game = tk.Toplevel(root)
    game.title(f"Play Tic Tac Toe {size}x{size}")
    board = [[" " for _ in range(size)] for _ in range(size)]
    current = ["X"]
    moves_made = [0]

    status = tk.StringVar(value=f"Player {current[0]}'s turn")
    ttk.Label(game, textvariable=status, font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=size, pady=(8,6))

    def check_winner(board):
        n = len(board)
        for i in range(n):
            if board[i][0] != " " and all(board[i][j] == board[i][0] for j in range(n)):
                return board[i][0]
            if board[0][i] != " " and all(board[j][i] == board[0][i] for j in range(n)):
                return board[0][i]
        if board[0][0] != " " and all(board[i][i] == board[0][0] for i in range(n)):
            return board[0][0]
        if board[0][n-1] != " " and all(board[i][n-1-i] == board[0][n-1] for i in range(n)):
            return board[0][n-1]
        return None

    def handle_click(r, c):
        if board[r][c] != " ":
            return
        board[r][c] = current[0]
        btns[r][c]["text"] = current[0]
        moves_made[0] += 1

        winner = check_winner(board)
        if winner:
            db_insert_game(winner=winner, board_size=size, moves_count=moves_made[0])
            messagebox.showinfo("Game Over", f"Player {winner} wins!")
            game.destroy()
            return

        if all(cell != " " for row in board for cell in row):
            db_insert_game(winner="Draw", board_size=size, moves_count=moves_made[0])
            messagebox.showinfo("Game Over", "It's a draw!")
            game.destroy()
            return

        current[0] = "O" if current[0] == "X" else "X"
        status.set(f"Player {current[0]}'s turn")

    btns = []
    for r in range(size):
        row_btns = []
        for c in range(size):
            b = tk.Button(game, text=" ", width=5, height=2, font=("Arial", 14, "bold"),
                          command=lambda r=r, c=c: handle_click(r, c))
            b.grid(row=r+1, column=c, padx=3, pady=3)
            row_btns.append(b)
        btns.append(row_btns)

def open_append_manual_window():
    win = tk.Toplevel(root)
    win.title("Append: Add Game Record (Manual)")
    frm = ttk.Frame(win, padding=12)
    frm.pack(fill="both", expand=True)

    ttk.Label(frm, text="Winner (X/O/Draw):").grid(row=0, column=0, sticky="e", pady=4, padx=4)
    winner_var = tk.StringVar(value="Draw")
    ttk.Combobox(frm, textvariable=winner_var, state="readonly", values=["X","O","Draw"], width=10).grid(row=0, column=1, sticky="w")

    ttk.Label(frm, text="Board Size (3/4/5):").grid(row=1, column=0, sticky="e", pady=4, padx=4)
    size_var = tk.IntVar(value=3)
    ttk.Combobox(frm, textvariable=size_var, state="readonly", values=[3,4,5], width=10).grid(row=1, column=1, sticky="w")

    ttk.Label(frm, text="Played At (YYYY-MM-DD HH:MM, optional):").grid(row=2, column=0, sticky="e", pady=4, padx=4)
    played_entry = ttk.Entry(frm, width=25)
    played_entry.grid(row=2, column=1, sticky="w")

    ttk.Label(frm, text="Moves Count (optional):").grid(row=3, column=0, sticky="e", pady=4, padx=4)
    moves_entry = ttk.Entry(frm, width=10)
    moves_entry.grid(row=3, column=1, sticky="w")

    def do_append():
        w = winner_var.get()
        s = int(size_var.get())
        played_at = played_entry.get().strip()
        moves_count = 0
        if moves_entry.get().strip():
            try:
                moves_count = int(moves_entry.get().strip())
            except ValueError:
                messagebox.showerror("Invalid", "Moves Count must be an integer")
                return

        if played_at:
            try:
                dt = datetime.strptime(played_at, "%Y-%m-%d %H:%M")
                played_at = dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                messagebox.showerror("Invalid", "Played At must be YYYY-MM-DD HH:MM")
                return
        else:
            played_at = None

        db_insert_game(w, s, played_at, moves_count)
        messagebox.showinfo("Done", "Game record appended.")
        win.destroy()

    ttk.Button(frm, text="Append Record", command=do_append).grid(row=4, column=0, columnspan=2, pady=10)

def open_view_window():
    win = tk.Toplevel(root)
    win.title("Game History")

    cols = ("ID", "Played At", "Winner", "Size", "Moves")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=15)
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=120, anchor="center")
    tree.pack(fill="both", expand=True)

    def do_refresh():
        populate_tree(tree, db_fetch_games())

    def delete_selected():
        sel = tree.selection()
        if not sel: return
        gid = tree.item(sel[0])["values"][0]
        db_delete_game(gid)
        do_refresh()

    def delete_all():
        db = connect_db()
        cur = db.cursor()
        cur.execute("DELETE FROM game_history")
        cur.execute("ALTER TABLE game_history AUTO_INCREMENT = 1")
        db.commit()
        db.close()
        do_refresh()

    btn_frame = ttk.Frame(win, padding=6)
    btn_frame.pack(fill="x")
    ttk.Button(btn_frame, text="Refresh", command=do_refresh).pack(side="left", padx=4)
    ttk.Button(btn_frame, text="Delete Selected", command=delete_selected).pack(side="left", padx=4)
    ttk.Button(btn_frame, text="Delete All", command=delete_all).pack(side="left", padx=4)

    do_refresh()

def open_search_window():
    win = tk.Toplevel(root)
    win.title("Search Games")

    frm = ttk.Frame(win, padding=6)
    frm.pack(fill="x")

    ttk.Label(frm, text="Winner:").grid(row=0, column=0, padx=4, pady=4)
    winner_var = tk.StringVar(value="")
    ttk.Combobox(frm, textvariable=winner_var, values=["","X","O","Draw"], width=10).grid(row=0, column=1)

    ttk.Label(frm, text="Date From (YYYY-MM-DD):").grid(row=1, column=0, padx=4, pady=4)
    from_entry = ttk.Entry(frm, width=12)
    from_entry.grid(row=1, column=1)

    ttk.Label(frm, text="Date To (YYYY-MM-DD):").grid(row=2, column=0, padx=4, pady=4)
    to_entry = ttk.Entry(frm, width=12)
    to_entry.grid(row=2, column=1)

    cols = ("ID", "Played At", "Winner", "Size", "Moves")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=120, anchor="center")
    tree.pack(fill="both", expand=True)

    def do_search():
        rows = db_search_games(
            winner=winner_var.get() if winner_var.get() else None,
            date_from=from_entry.get().strip() or None,
            date_to=to_entry.get().strip() or None
        )
        populate_tree(tree, rows)

    ttk.Button(frm, text="Search", command=do_search).grid(row=3, column=0, columnspan=2, pady=6)

def open_sort_window():
    win = tk.Toplevel(root)
    win.title("Sort Games")

    frm = ttk.Frame(win, padding=6)
    frm.pack(fill="x")

    ttk.Label(frm, text="Sort by:").grid(row=0, column=0, padx=4, pady=4)
    field_var = tk.StringVar(value="played_at")
    ttk.Combobox(frm, textvariable=field_var, values=["game_id","played_at","winner","board_size","moves_count"], width=12).grid(row=0, column=1)

    ttk.Label(frm, text="Order:").grid(row=1, column=0, padx=4, pady=4)
    order_var = tk.StringVar(value="DESC")
    ttk.Combobox(frm, textvariable=order_var, values=["ASC","DESC"], width=12).grid(row=1, column=1)

    cols = ("ID", "Played At", "Winner", "Size", "Moves")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=120, anchor="center")
    tree.pack(fill="both", expand=True)

    def do_sort():
        rows = db_fetch_games(order_by=field_var.get(), asc=(order_var.get()=="ASC"))
        populate_tree(tree, rows)

    ttk.Button(frm, text="Apply Sort", command=do_sort).grid(row=2, column=0, columnspan=2, pady=6)

def open_help_window():
    win = tk.Toplevel(root)
    win.title("Help / Instructions")
    txt = tk.Text(win, wrap="word", width=80, height=26)
    txt.pack(fill="both", expand=True)
    txt.insert("1.0", """
TIC TAC TOE PROJECT — Python + Tkinter + MySQL
• The game is played on a grid (3x3, 4x4, or 5x5 depending on your choice).
• Two players take turns marking empty squares:
• Player 1 uses X
• Player 2 uses O
• Players alternate turns until one player wins or the board is full.
• A player wins if they place their symbols in a straight line:Horizontally, Vertically, Diagonally

If all squares are filled and no player has a winning line, the game ends in a draw.
FEATURES
• Play Game: 3x3, 4x4, or 5x5 (X vs O). Playing appends a record.
• Append: Manual form to add a game record.
• View/Display: Game History (with Moves Count).
• Search: Filter history by winner, date range.
• Delete: Remove a game.
• Sort: Sort by played_at / game_id / winner / size / moves.
""")
    txt.config(state="disabled")

# ---------------------- MAIN WINDOW ----------------------
def build_main_window():
    root.title("Tic Tac Toe Project — Python & MySQL")
    container = ttk.Frame(root, padding=12)
    container.pack(fill="both", expand=True)

    title = ttk.Label(container, text="TIC TAC TOE PROJECT", font=("Arial", 18, "bold"))
    title.grid(row=0, column=0, columnspan=3, pady=(0,12))

    ttk.Button(container, text="Play 3 x 3", width=22, command=lambda: open_play_window(3)).grid(row=1, column=0, padx=6, pady=6)
    ttk.Button(container, text="Play 4 x 4", width=22, command=lambda: open_play_window(4)).grid(row=1, column=1, padx=6, pady=6)
    ttk.Button(container, text="Play 5 x 5", width=22, command=lambda: open_play_window(5)).grid(row=1, column=2, padx=6, pady=6)

    ttk.Button(container, text="Append (Manual)", width=22, command=open_append_manual_window).grid(row=2, column=0, padx=6, pady=6)
    ttk.Button(container, text="View / Display", width=22, command=open_view_window).grid(row=2, column=1, padx=6, pady=6)
    ttk.Button(container, text="Search", width=22, command=open_search_window).grid(row=2, column=2, padx=6, pady=6)
    ttk.Button(container, text="Help", width=22, command=open_help_window).grid(row=3, column=0, padx=6, pady=6)
    ttk.Button(container, text="Delete", width=22, command=open_view_window).grid(row=3, column=1, padx=6, pady=6)
    ttk.Button(container, text="Sort", width=22, command=open_sort_window).grid(row=3, column=2, padx=6, pady=6)
    ttk.Button(container, text="Exit", width=22, command=root.quit).grid(row=4, column=1, padx=6, pady=10)
    # ---------------------- RUN APP ----------------------
if __name__ == "__main__":
    create_tables()
    root = tk.Tk()
    try:
        s = ttk.Style()
        if "clam" in s.theme_names():
            s.theme_use("clam")
    except Exception:
        pass
    build_main_window()
    root.mainloop()
