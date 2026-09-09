"""
Панель инструментов для добавления блоков
"""
import tkinter as tk
from tkinter import ttk
from logic_trainer.core import BlockType


class Toolbar(ttk.Frame):
    """Панель инструментов с кнопками блоков"""

    def __init__(self, parent, canvas, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.canvas = canvas
        self.circuit = canvas.circuit

        self.setup_ui()

    def update_circuit_reference(self, circuit, canvas):
        """Обновить ссылки на схему и холст"""
        self.circuit = circuit
        self.canvas = canvas
        self.update_stats()  # Обновить статистику

    def setup_ui(self):
        """Настроить интерфейс панели инструментов"""
        # Заголовок
        title = ttk.Label(self, text="Блоки", font=('Arial', 10, 'bold'))
        title.pack(pady=5)

        # Кнопки для добавления блоков
        block_types = [
            ("Вход", BlockType.INPUT, "#e6f3ff"),
            ("Выход", BlockType.OUTPUT, "#fff0e6"),
            ("AND", BlockType.AND, "#e6ffe6"),
            ("OR", BlockType.OR, "#ffe6e6"),
            ("NOT", BlockType.NOT, "#f0e6ff"),
            ("XOR", BlockType.XOR, "#fffae6"),
            ("NAND", BlockType.NAND, "#ffe6ff"),
            ("NOR", BlockType.NOR, "#ffffe6")
        ]

        for name, block_type, color in block_types:
            btn_frame = ttk.Frame(self)
            btn_frame.pack(fill=tk.X, pady=2, padx=5)

            # Цветной индикатор
            color_label = tk.Label(btn_frame, bg=color, width=3, height=1)
            color_label.pack(side=tk.LEFT, padx=(0, 5))

            # Кнопка
            btn = ttk.Button(
                btn_frame,
                text=name,
                command=lambda bt=block_type: self.add_block(bt),
                width=12
            )
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Разделитель
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Режимы работы
        mode_label = ttk.Label(self, text="Режим", font=('Arial', 10, 'bold'))
        mode_label.pack(pady=5)

        self.mode_var = tk.StringVar(value="select")

        modes = [
            ("Выбор", "select"),
            ("Соединение", "connect"),
        ]

        for text, value in modes:
            rb = ttk.Radiobutton(
                self,
                text=text,
                variable=self.mode_var,
                value=value,
                command=self.on_mode_changed
            )
            rb.pack(anchor=tk.W, padx=10, pady=2)

        # Разделитель
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Статистика
        stats_label = ttk.Label(self, text="Статистика", font=('Arial', 10, 'bold'))
        stats_label.pack(pady=5)

        self.stats_frame = ttk.Frame(self)
        self.stats_frame.pack(fill=tk.X, padx=5)

        self.blocks_label = ttk.Label(self.stats_frame, text="Блоки: 0")
        self.blocks_label.pack(anchor=tk.W)

        self.connections_label = ttk.Label(self.stats_frame, text="Соединения: 0")
        self.connections_label.pack(anchor=tk.W)

        # Кнопки управления
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        control_label = ttk.Label(self, text="Управление", font=('Arial', 10, 'bold'))
        control_label.pack(pady=5)

        self.clear_btn = ttk.Button(
            self,
            text="Очистить все",
            command=self.clear_all,
            width=15
        )
        self.clear_btn.pack(pady=2, padx=5)

        self.layout_btn = ttk.Button(
            self,
            text="Авто-расположение",
            command=self.auto_layout,
            width=15
        )
        self.layout_btn.pack(pady=2, padx=5)
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # test_label = ttk.Label(self, text="Тесты", font=('Arial', 10, 'bold'))
        # test_label.pack(pady=5)
        #
        # self.add_test_btn = ttk.Button(
        #     self,
        #     text="Создать тест",
        #     command=self.create_test_from_current,
        #     width=15
        # )
        # self.add_test_btn.pack(pady=2, padx=5)

    def create_test_from_current(self):
        """Создать тестовый случай из текущего состояния"""
        # Находим родительское окно
        parent = self.winfo_toplevel()

        # Получаем ссылку на приложение (немного хак)
        if hasattr(parent, 'app'):
            parent.app.add_test_from_current_state()

    def add_block(self, block_type: BlockType):
        """Добавить новый блок на холст"""
        from logic_trainer.core import LogicBlock

        # Создаем блок
        block = LogicBlock(block_type)

        # Позиция по умолчанию (центр видимой области)
        x = self.canvas.winfo_width() // 2 - 40
        y = self.canvas.winfo_height() // 2 - 25

        # Корректируем если холст пустой
        if x < 0:
            x = 50
        if y < 0:
            y = 50

        block.x = x
        block.y = y

        # Добавляем в схему
        self.circuit.add_block(block)

        # ВЫЗЫВАЕМ АВТОРАСПОЛОЖЕНИЕ
        self.auto_layout()

        # Генерируем событие изменения схемы
        self.canvas.parent.event_generate('<<CircuitChanged>>')
    def on_mode_changed(self):
        """Обработка изменения режима"""
        mode = self.mode_var.get()
        # Пока просто меняем курсор
        if mode == "select":
            self.canvas.config(cursor="arrow")
        elif mode == "connect":
            self.canvas.config(cursor="cross")

    def update_stats(self):
        """Обновить статистику на панели"""
        blocks_count = len(self.circuit.blocks)
        connections_count = len(self.circuit.connections)

        self.blocks_label.config(text=f"Блоки: {blocks_count}")
        self.connections_label.config(text=f"Соединения: {connections_count}")

    def clear_all(self):
        """Очистить всю схему"""
        # Удаляем все блоки
        block_ids = list(self.circuit.blocks.keys())
        for block_id in block_ids:
            self.circuit.remove_block(block_id)

        self.canvas.redraw()
        self.update_stats()
        self.canvas.parent.event_generate('<<CircuitChanged>>')

    def auto_layout(self):
        """Автоматическое расположение блоков"""
        if not self.circuit.blocks:
            return

        # Простой алгоритм: входы слева, логические в центре, выходы справа
        input_blocks = []
        logic_blocks = []
        output_blocks = []

        for block in self.circuit.blocks.values():
            if block.type == BlockType.INPUT:
                input_blocks.append(block)
            elif block.type == BlockType.OUTPUT:
                output_blocks.append(block)
            else:
                logic_blocks.append(block)

        # Располагаем входы
        for i, block in enumerate(input_blocks):
            block.x = 50
            block.y = 50 + i * 100

        # Располагаем логические блоки
        for i, block in enumerate(logic_blocks):
            block.x = 200
            block.y = 50 + i * 100

        # Располагаем выходы
        for i, block in enumerate(output_blocks):
            block.x = 350
            block.y = 50 + i * 100

        self.canvas.redraw()