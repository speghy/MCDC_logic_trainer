"""
Панель свойств выбранного элемента
"""
import tkinter as tk
from tkinter import ttk, messagebox
from logic_trainer.core import LogicBlock, BlockType


class PropertiesPanel(ttk.Frame):
    """Панель свойств выбранного блока"""

    def __init__(self, parent, canvas, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.canvas = canvas

        # Подписка на события
        self.canvas.bind('<<SelectionChanged>>', self.on_selection_changed)
        self.canvas.bind('<<BlockValueChanged>>', self.on_value_changed)

        self.setup_ui()
        self.current_block = None

    def setup_ui(self):
        """Настроить интерфейс панели свойств"""
        # Заголовок
        title = ttk.Label(self, text="Свойства", font=('Arial', 10, 'bold'))
        title.pack(pady=5)

        # Область свойств
        self.props_frame = ttk.Frame(self)
        self.props_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Заглушка при отсутствии выбора
        self.placeholder = ttk.Label(
            self.props_frame,
            text="Выберите блок для просмотра свойств",
            font=('Arial', 9),
            foreground='gray'
        )
        self.placeholder.pack(pady=20)

        # Переменные для свойств
        self.name_var = tk.StringVar()
        self.value_var = tk.BooleanVar()
        self.block_type_var = tk.StringVar()

        # Элементы управления (создаются динамически)
        self.name_label = None
        self.name_entry = None
        self.value_label = None
        self.value_check = None
        self.type_label = None
        self.type_value = None
        self.connections_frame = None

        # Кнопка обновления
        self.update_btn = ttk.Button(
            self,
            text="Обновить",
            command=self.update_block_properties,
            state='disabled'
        )
        self.update_btn.pack(pady=10, padx=5)

    def on_selection_changed(self, event=None):
        """Обработка изменения выбора"""
        self.current_block = self.canvas.selected_block

        # Очищаем старые виджеты
        self.clear_properties()

        if self.current_block:
            self.show_block_properties(self.current_block)
            self.update_btn.config(state='normal')
        else:
            self.placeholder.pack(pady=20)
            self.update_btn.config(state='disabled')

    def on_value_changed(self, event=None):
        """Обработка изменения значения блока"""
        if self.current_block:
            self.value_var.set(self.current_block.value or False)

    def clear_properties(self):
        """Очистить все виджеты свойств"""
        for widget in self.props_frame.winfo_children():
            widget.destroy()

    def show_block_properties(self, block: LogicBlock):
        """Показать свойства выбранного блока"""
        # Название блока
        ttk.Label(self.props_frame, text="Название:", font=('Arial', 9, 'bold')).pack(anchor=tk.W, pady=(5, 0))
        self.name_var.set(block.name)
        self.name_entry = ttk.Entry(self.props_frame, textvariable=self.name_var, width=20)
        self.name_entry.pack(fill=tk.X, pady=(0, 10))

        # Тип блока
        ttk.Label(self.props_frame, text="Тип:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        self.block_type_var.set(block.type.value)
        type_value = ttk.Label(self.props_frame, text=block.type.value, font=('Arial', 9))
        type_value.pack(anchor=tk.W, pady=(0, 10))

        # Значение (для INPUT блоков)
        if block.type == BlockType.INPUT:
            ttk.Label(self.props_frame, text="Значение:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
            self.value_var.set(block.value or False)
            self.value_check = ttk.Checkbutton(
                self.props_frame,
                text="Истина (1)" if block.value else "Ложь (0)",
                variable=self.value_var,
                command=self.on_checkbox_toggle
            )
            self.value_check.pack(anchor=tk.W, pady=(0, 10))

        # Соединения
        self.show_connections(block)

    def show_connections(self, block: LogicBlock):
        """Показать информацию о соединениях"""
        # Входные соединения
        if block.input_connections:
            ttk.Label(self.props_frame, text="Входные соединения:", font=('Arial', 9, 'bold')).pack(anchor=tk.W,
                                                                                                    pady=(10, 0))

            for i, conn_id in enumerate(block.input_connections):
                if conn_id:
                    conn = self.canvas.circuit.connections.get(conn_id)
                    if conn:
                        source_block = self.canvas.circuit.blocks.get(conn.source_id)
                        if source_block:
                            label = f"Порт {i}: {source_block.name} ({source_block.type.value})"
                            ttk.Label(self.props_frame, text=label, font=('Arial', 8)).pack(anchor=tk.W)

        # Выходные соединения
        if block.output_connections:
            ttk.Label(self.props_frame, text="Выходные соединения:", font=('Arial', 9, 'bold')).pack(anchor=tk.W,
                                                                                                     pady=(10, 0))

            for conn_id in block.output_connections:
                conn = self.canvas.circuit.connections.get(conn_id)
                if conn:
                    target_block = self.canvas.circuit.blocks.get(conn.target_id)
                    if target_block:
                        label = f"→ {target_block.name} ({target_block.type.value}) порт {conn.target_port}"
                        ttk.Label(self.props_frame, text=label, font=('Arial', 8)).pack(anchor=tk.W)

    def on_checkbox_toggle(self):
        """Обработка переключения чекбокса значения"""
        if self.current_block and self.current_block.type == BlockType.INPUT:
            self.current_block.value = self.value_var.get()
            # Обновляем текст чекбокса
            self.value_check.config(text="Истина (1)" if self.value_var.get() else "Ложь (0)")

            # Запускаем симуляцию
            self.canvas.simulator.propagate_signal(self.current_block.id)

            # Перерисовываем холст
            self.canvas.redraw()

            # Генерируем событие
            self.canvas.parent.event_generate('<<BlockValueChanged>>')

    def update_block_properties(self):
        """Обновить свойства блока"""
        if not self.current_block:
            return

        # Обновляем имя
        new_name = self.name_var.get().strip()
        if new_name and new_name != self.current_block.name:
            self.current_block.name = new_name
            self.canvas.redraw()
            messagebox.showinfo("Успех", "Имя блока обновлено")