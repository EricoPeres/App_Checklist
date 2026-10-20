import os
import sqlite3
import sys
import tkinter as tk
from xml.sax.saxutils import escape
from tkinter import messagebox, ttk
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _base_dir():
    """Pasta do script (ou do .exe, se empacotado com PyInstaller)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# O banco fica sempre ao lado do programa, não importa de onde ele foi executado
DB_PATH = os.path.join(_base_dir(), "checklist.db")


class ChecklistApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Gerenciador de Checklists")
        self.root.geometry("820x550")  # Aumentado para acomodar os novos botões
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.current_checklist_id = None
        self.current_checklist_name = ""

        # Inicializa Banco de Dados
        self.init_db()

        # Inicia na Tela de Gerenciamento de Checklists
        self.show_checklist_manager()

    def init_db(self):
        """Cria e ajusta as tabelas no SQLite3."""
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON;")

        # Tabela de Checklists
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS checklists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE
            )
        """
        )

        # Tabela de Tarefas
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tarefas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checklist_id INTEGER NOT NULL,
                descricao TEXT NOT NULL,
                concluida INTEGER DEFAULT 0,
                ordem INTEGER DEFAULT 0,
                FOREIGN KEY (checklist_id) REFERENCES checklists (id) ON DELETE CASCADE
            )
        """
        )

        # Garante a coluna 'ordem' caso o banco antigo já exista
        self.cursor.execute("PRAGMA table_info(tarefas)")
        columns = [column[1] for column in self.cursor.fetchall()]
        if "ordem" not in columns:
            self.cursor.execute(
                "ALTER TABLE tarefas ADD COLUMN ordem INTEGER DEFAULT 0"
            )

        self.conn.commit()

    def clear_screen(self):
        """Limpa todos os widgets da janela."""
        for widget in self.root.winfo_children():
            widget.destroy()

    # ==========================================
    # TELA 1: GERENCIADOR DE CHECKLISTS
    # ==========================================
    def show_checklist_manager(self):
        self.clear_screen()
        self.current_checklist_id = None
        self.current_checklist_name = ""

        # Frame Superior - Cadastro de Novo Checklist
        frame_input = ttk.LabelFrame(
            self.root, text=" Criar Novo Checklist ", padding="10"
        )
        frame_input.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame_input, text="Nome do Checklist:").pack(
            side=tk.LEFT, padx=(0, 5)
        )
        self.entry_checklist_name = ttk.Entry(frame_input, width=35)
        self.entry_checklist_name.pack(side=tk.LEFT, padx=(0, 5))
        self.entry_checklist_name.bind(
            "<Return>", lambda e: self.create_checklist()
        )

        btn_create = ttk.Button(
            frame_input, text="Criar", command=self.create_checklist
        )
        btn_create.pack(side=tk.LEFT)

        # Frame Central - Lista de Checklists Cadastrados
        frame_list = ttk.LabelFrame(
            self.root, text=" Checklists Cadastrados ", padding="10"
        )
        frame_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("id", "nome")
        self.tree_checklists = ttk.Treeview(
            frame_list, columns=columns, show="headings", selectmode="browse"
        )
        self.tree_checklists.heading("id", text="ID")
        self.tree_checklists.heading("nome", text="Nome do Checklist")

        self.tree_checklists.column("id", width=50, anchor=tk.CENTER)
        self.tree_checklists.column("nome", width=650, anchor=tk.W)

        scrollbar = ttk.Scrollbar(
            frame_list, orient=tk.VERTICAL, command=self.tree_checklists.yview
        )
        self.tree_checklists.configure(yscrollcommand=scrollbar.set)

        self.tree_checklists.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_checklists.bind("<Double-1>", lambda e: self.open_checklist())

        # Frame Inferior - Ações da Tela Inicial
        frame_actions = ttk.Frame(self.root, padding="10")
        frame_actions.pack(fill=tk.X, padx=10)

        btn_open = ttk.Button(
            frame_actions, text="Abrir Checklist", command=self.open_checklist
        )
        btn_open.pack(side=tk.LEFT, padx=5)

        btn_delete_cl = ttk.Button(
            frame_actions,
            text="Excluir Checklist Inteiro",
            command=self.delete_checklist,
        )
        btn_delete_cl.pack(side=tk.LEFT, padx=5)

        self.load_checklists()

    def load_checklists(self):
        """Carrega a lista de checklists cadastrados."""
        for item in self.tree_checklists.get_children():
            self.tree_checklists.delete(item)

        self.cursor.execute("SELECT id, nome FROM checklists ORDER BY id DESC")
        for row in self.cursor.fetchall():
            self.tree_checklists.insert("", tk.END, values=row)

    def create_checklist(self):
        """Cria um novo checklist."""
        nome = self.entry_checklist_name.get().strip()
        if not nome:
            messagebox.showwarning(
                "Aviso", "Digite um nome para o novo checklist."
            )
            return

        try:
            self.cursor.execute(
                "INSERT INTO checklists (nome) VALUES (?)", (nome,)
            )
            self.conn.commit()
            self.entry_checklist_name.delete(0, tk.END)
            self.load_checklists()
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Erro", "Já existe um checklist cadastrado com esse nome."
            )

    def open_checklist(self):
        """Abre a tela de detalhes do checklist selecionado."""
        selected = self.tree_checklists.selection()
        if not selected:
            messagebox.showwarning(
                "Aviso", "Selecione um checklist para abrir."
            )
            return

        item = self.tree_checklists.item(selected, "values")
        self.current_checklist_id = item[0]
        self.current_checklist_name = item[1]

        self.show_task_manager()

    def delete_checklist(self):
        """Exclui um checklist inteiro."""
        selected = self.tree_checklists.selection()
        if not selected:
            messagebox.showwarning(
                "Aviso", "Selecione um checklist para excluir."
            )
            return

        item = self.tree_checklists.item(selected, "values")
        cl_id, cl_nome = item[0], item[1]

        confirm = messagebox.askyesno(
            "Confirmação",
            f"Tem certeza que deseja excluir o checklist '{cl_nome}'?\n"
            "Todas as tarefas associadas a ele serão apagadas permanentemente!",
        )

        if confirm:
            self.cursor.execute("PRAGMA foreign_keys = ON;")
            self.cursor.execute(
                "DELETE FROM checklists WHERE id = ?", (cl_id,)
            )
            self.conn.commit()
            self.load_checklists()

    # ==========================================
    # TELA 2: GERENCIADOR DE TAREFAS
    # ==========================================
    def show_task_manager(self):
        self.clear_screen()

        # Cabeçalho com Nome do Checklist
        frame_header = ttk.Frame(self.root, padding="5 10 5 0")
        frame_header.pack(fill=tk.X, padx=10)

        btn_back = ttk.Button(
            frame_header,
            text="⬅ Voltar",
            command=self.show_checklist_manager,
        )
        btn_back.pack(side=tk.LEFT)

        lbl_title = ttk.Label(
            frame_header,
            text=f"Checklist: {self.current_checklist_name}",
            font=("Helvetica", 12, "bold"),
        )
        lbl_title.pack(side=tk.LEFT, padx=15)

        # Frame Superior (Inclusão de Tarefas)
        frame_input = ttk.Frame(self.root, padding="10")
        frame_input.pack(fill=tk.X, padx=10)

        self.entry_task = ttk.Entry(frame_input, width=40)
        self.entry_task.pack(side=tk.LEFT, padx=(0, 5))
        self.entry_task.bind("<Return>", lambda e: self.add_task())

        btn_add = ttk.Button(
            frame_input, text="Adicionar Tarefa", command=self.add_task
        )
        btn_add.pack(side=tk.LEFT)

        # Frame Central (Tabela de Tarefas + Botões laterais)
        frame_list = ttk.Frame(self.root, padding="10")
        frame_list.pack(fill=tk.BOTH, expand=True, padx=10)

        frame_reorder = ttk.Frame(frame_list)
        frame_reorder.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))

        btn_up = ttk.Button(
            frame_reorder,
            text="▲ Subir",
            width=10,
            command=lambda: self.move_task(-1),
        )
        btn_up.pack(pady=(20, 5))

        btn_down = ttk.Button(
            frame_reorder,
            text="▼ Descer",
            width=10,
            command=lambda: self.move_task(1),
        )
        btn_down.pack(pady=5)

        columns = ("pos", "id", "descricao", "status")
        self.tree_tasks = ttk.Treeview(
            frame_list, columns=columns, show="headings", selectmode="browse"
        )

        self.tree_tasks.heading("pos", text="Nº")
        self.tree_tasks.heading("id", text="ID")
        self.tree_tasks.heading("descricao", text="Descrição da Tarefa")
        self.tree_tasks.heading("status", text="Status")

        self.tree_tasks.column("pos", width=40, anchor=tk.CENTER)
        self.tree_tasks.column("id", width=40, anchor=tk.CENTER)
        self.tree_tasks.column("descricao", width=450, anchor=tk.W)
        self.tree_tasks.column("status", width=120, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(
            frame_list, orient=tk.VERTICAL, command=self.tree_tasks.yview
        )
        self.tree_tasks.configure(yscrollcommand=scrollbar.set)

        self.tree_tasks.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        # Frame Inferior (Ações de Tarefas e Exportação)
        frame_actions = ttk.Frame(self.root, padding="10")
        frame_actions.pack(fill=tk.X, padx=10)

        btn_toggle = ttk.Button(
            frame_actions,
            text="Alternar Status",
            command=self.toggle_task,
        )
        btn_toggle.pack(side=tk.LEFT, padx=2)

        btn_transfer = ttk.Button(
            frame_actions,
            text="⇄ Transferir Tarefa",
            command=self.transfer_task,
        )
        btn_transfer.pack(side=tk.LEFT, padx=2)

        btn_delete = ttk.Button(
            frame_actions, text="Excluir Tarefa", command=self.delete_task
        )
        btn_delete.pack(side=tk.LEFT, padx=2)

        btn_excel = ttk.Button(
            frame_actions, text="Exportar p/ Excel", command=self.export_excel
        )
        btn_excel.pack(side=tk.RIGHT, padx=2)

        btn_pdf = ttk.Button(
            frame_actions, text="Exportar p/ PDF", command=self.export_pdf
        )
        btn_pdf.pack(side=tk.RIGHT, padx=2)

        self.load_tasks()

    def load_tasks(self, select_id=None):
        """Carrega as tarefas ordenadas pelo campo 'ordem'."""
        for item in self.tree_tasks.get_children():
            self.tree_tasks.delete(item)

        self.cursor.execute(
            "SELECT id, descricao, concluida FROM tarefas WHERE checklist_id = ? ORDER BY ordem ASC, id ASC",
            (self.current_checklist_id,),
        )
        rows = self.cursor.fetchall()

        for index, row in enumerate(rows, start=1):
            task_id, desc, concluida = row
            status = "✔ Concluída" if concluida else "⏳ Pendente"
            item_id = self.tree_tasks.insert(
                "", tk.END, values=(index, task_id, desc, status)
            )

            if select_id and task_id == select_id:
                self.tree_tasks.selection_set(item_id)
                self.tree_tasks.focus(item_id)

    def add_task(self):
        """Adiciona tarefa ao checklist atual."""
        desc = self.entry_task.get().strip()
        if desc:
            self.cursor.execute(
                "SELECT MAX(ordem) FROM tarefas WHERE checklist_id = ?",
                (self.current_checklist_id,),
            )
            max_ordem = self.cursor.fetchone()[0]
            next_ordem = (max_ordem + 1) if max_ordem is not None else 1

            self.cursor.execute(
                "INSERT INTO tarefas (checklist_id, descricao, concluida, ordem) VALUES (?, ?, 0, ?)",
                (self.current_checklist_id, desc, next_ordem),
            )
            self.conn.commit()
            self.entry_task.delete(0, tk.END)
            self.load_tasks()
        else:
            messagebox.showwarning("Aviso", "Digite uma descrição para a tarefa.")

    def move_task(self, direction):
        """Move a tarefa selecionada para cima (-1) ou para baixo (+1)."""
        selected = self.tree_tasks.selection()
        if not selected:
            messagebox.showwarning(
                "Aviso", "Selecione uma tarefa para alterar a ordem."
            )
            return

        self.cursor.execute(
            "SELECT id, ordem FROM tarefas WHERE checklist_id = ? ORDER BY ordem ASC, id ASC",
            (self.current_checklist_id,),
        )
        tasks = self.cursor.fetchall()

        selected_id = int(self.tree_tasks.item(selected, "values")[1])

        index = next(
            (i for i, t in enumerate(tasks) if t[0] == selected_id), None
        )
        if index is None:
            return

        new_index = index + direction
        if 0 <= new_index < len(tasks):
            ids = [t[0] for t in tasks]
            ids[index], ids[new_index] = ids[new_index], ids[index]
            curr_id = selected_id

            # Renumera toda a lista de 1..N para manter a ordem consistente
            for pos, tid in enumerate(ids, start=1):
                self.cursor.execute(
                    "UPDATE tarefas SET ordem = ? WHERE id = ?", (pos, tid)
                )
            self.conn.commit()

            self.load_tasks(select_id=curr_id)

    def transfer_task(self):
        """Abre uma janela popup para transferir a tarefa para outro checklist."""
        selected = self.tree_tasks.selection()
        if not selected:
            messagebox.showwarning(
                "Aviso", "Selecione uma tarefa para transferir."
            )
            return

        item_values = self.tree_tasks.item(selected, "values")
        task_id = item_values[1]
        task_desc = item_values[2]

        # Busca todos os outros checklists disponíveis
        self.cursor.execute(
            "SELECT id, nome FROM checklists WHERE id != ? ORDER BY nome ASC",
            (self.current_checklist_id,),
        )
        other_checklists = self.cursor.fetchall()

        if not other_checklists:
            messagebox.showwarning(
                "Aviso",
                "Não existem outros checklists para onde transferir esta tarefa.",
            )
            return

        # Pop-up de Transferência
        dialog = tk.Toplevel(self.root)
        dialog.title("Transferir Tarefa")
        dialog.geometry("380x160")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(
            dialog,
            text=f"Transferir: '{task_desc[:30]}...'",
            font=("Helvetica", 9, "bold"),
        ).pack(pady=(15, 5))
        ttk.Label(dialog, text="Selecione o checklist de destino:").pack(pady=2)

        checklist_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in other_checklists}
        combo = ttk.Combobox(
            dialog, values=list(checklist_dict.keys()), state="readonly", width=35
        )
        combo.pack(pady=5)
        combo.current(0)

        def confirm_transfer():
            target_cl_id = checklist_dict[combo.get()]

            # Pega a próxima ordem no checklist de destino
            self.cursor.execute(
                "SELECT MAX(ordem) FROM tarefas WHERE checklist_id = ?",
                (target_cl_id,),
            )
            max_ordem = self.cursor.fetchone()[0]
            next_ordem = (max_ordem + 1) if max_ordem is not None else 1

            # Atualiza o checklist_id e a ordem no BD
            self.cursor.execute(
                "UPDATE tarefas SET checklist_id = ?, ordem = ? WHERE id = ?",
                (target_cl_id, next_ordem, task_id),
            )
            self.conn.commit()

            dialog.destroy()
            messagebox.showinfo("Sucesso", "Tarefa transferida com sucesso!")
            self.load_tasks()

        btn_confirm = ttk.Button(
            dialog, text="Confirmar Transferência", command=confirm_transfer
        )
        btn_confirm.pack(pady=10)

    def toggle_task(self):
        """Alterna status da tarefa."""
        selected_item = self.tree_tasks.selection()
        if not selected_item:
            messagebox.showwarning(
                "Aviso", "Selecione uma tarefa para alterar o status."
            )
            return

        item_values = self.tree_tasks.item(selected_item, "values")
        task_id = item_values[1]
        current_status = item_values[3]

        new_status = 0 if "✔" in current_status else 1
        self.cursor.execute(
            "UPDATE tarefas SET concluida = ? WHERE id = ?",
            (new_status, task_id),
        )
        self.conn.commit()
        self.load_tasks(select_id=int(task_id))

    def delete_task(self):
        """Remove a tarefa selecionada."""
        selected_item = self.tree_tasks.selection()
        if not selected_item:
            messagebox.showwarning("Aviso", "Selecione uma tarefa para excluir.")
            return

        task_id = self.tree_tasks.item(selected_item, "values")[1]
        self.cursor.execute("DELETE FROM tarefas WHERE id = ?", (task_id,))
        self.conn.commit()
        self.load_tasks()

    # ==========================================
    # EXPORTAÇÕES
    # ==========================================
    def sanitize_filename(self, name):
        """Trata o nome do checklist para gerar um nome de arquivo válido."""
        return "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).rstrip()

    def export_excel(self):
        """Exporta o checklist aberto para Excel respeitando a ordem."""
        df = pd.read_sql_query(
            """
            SELECT ROW_NUMBER() OVER (ORDER BY ordem ASC, id ASC) AS 'Nº',
                   descricao AS 'Descrição', 
                   CASE WHEN concluida = 1 THEN 'Concluída' ELSE 'Pendente' END AS 'Status' 
            FROM tarefas 
            WHERE checklist_id = ?
            ORDER BY ordem ASC, id ASC
        """,
            self.conn,
            params=(self.current_checklist_id,),
        )

        safe_title = self.sanitize_filename(self.current_checklist_name)
        filename = f"{safe_title}.xlsx"

        try:
            df.to_excel(filename, index=False)
            messagebox.showinfo(
                "Sucesso", f"Checklist exportado para Excel: {filename}"
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar Excel: {e}")

    def export_pdf(self):
        """Exporta o checklist aberto para PDF respeitando a ordem."""
        safe_title = self.sanitize_filename(self.current_checklist_name)
        filename = f"{safe_title}.pdf"

        try:
            doc = SimpleDocTemplate(
                filename,
                pagesize=letter,
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30,
            )
            elements = []

            styles = getSampleStyleSheet()
            title_style = styles["Heading1"]
            title_style.alignment = 1

            elements.append(
                Paragraph(
                    f"Checklist: {escape(self.current_checklist_name)}", title_style
                )
            )
            elements.append(Spacer(1, 15))

            data = [["Nº", "Descrição da Tarefa", "Status"]]

            self.cursor.execute(
                "SELECT descricao, concluida FROM tarefas WHERE checklist_id = ? ORDER BY ordem ASC, id ASC",
                (self.current_checklist_id,),
            )
            rows = self.cursor.fetchall()

            cell_style = ParagraphStyle(
                name="NormalCell", fontName="Helvetica", fontSize=10
            )

            for index, row in enumerate(rows, start=1):
                pos = str(index)
                desc = Paragraph(escape(row[0]), cell_style)
                status = "Concluída" if row[1] == 1 else "Pendente"
                data.append([pos, desc, status])

            table = Table(data, colWidths=[40, 400, 100])
            table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor("#2196F3"),
                        ),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("ALIGN", (0, 0), (0, -1), "CENTER"),
                        ("ALIGN", (2, 0), (2, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 11),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#F2F2F2")],
                        ),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )

            elements.append(table)
            doc.build(elements)

            messagebox.showinfo(
                "Sucesso", f"Checklist exportado para PDF: {filename}"
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar PDF: {e}")

    def on_close(self):
        """Fecha o banco de dados e a janela de forma segura."""
        try:
            self.conn.close()
        finally:
            self.root.destroy()


def main():
    """Ponto de entrada do checklist (chamado pela tela de abertura)."""
    root = tk.Tk()
    app = ChecklistApp(root)

    # Centraliza a janela na tela
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")

    root.mainloop()


if __name__ == "__main__":
    main()