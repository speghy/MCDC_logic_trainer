"""
Таблица тестовых случаев
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Callable
from logic_trainer.core.test_cases import TestSuite, TestCase
from logic_trainer.core.block import BlockType


class TestTable(ttk.Frame):
    """Таблица тестовых случаев"""

    def __init__(self, parent, test_suite: TestSuite,
                 on_case_selected: Callable = None,
                 app_reference = None):  # ← ДОБАВИЛИ!
        super().__init__(parent)
        self.test_suite = test_suite
        self.on_case_selected = on_case_selected
        self.app_reference = app_reference  # ← Сохраняем ссылку

        self.setup_ui()
        self.refresh_table()

    def setup_ui(self):
        """Настроить интерфейс таблицы"""
        # Верхняя панель с кнопками управления
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Заголовок
        title = ttk.Label(control_frame, text="Тестовые случаи",
                          font=('Arial', 10, 'bold'))
        title.pack(side=tk.LEFT, padx=5)

        # Панель кнопок справа
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side=tk.RIGHT)

        # Кнопки управления
        ttk.Button(btn_frame, text="+ Добавить",
                   command=self.add_test_case_dialog,
                   width=15).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="✎ Изменить",
                   command=self.edit_test_case,
                   width=15).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="✗ Удалить",
                   command=self.delete_test_case,
                   width=15).pack(side=tk.LEFT, padx=2)

        # Разделитель
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5)

        # Основной контейнер для таблицы
        table_container = ttk.Frame(self)
        table_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Таблица с полосами прокрутки
        columns = ("#", "Название", "Входы", "Ожидается", "Результат")
        self.tree = ttk.Treeview(table_container, columns=columns,
                                 show="headings", height=10)

        # Настройка колонок
        self.tree.column("#", width=40, anchor=tk.CENTER)
        self.tree.column("Название", width=100)
        self.tree.column("Входы", width=150)
        self.tree.column("Ожидается", width=150)
        self.tree.column("Результат", width=100)

        for col in columns:
            self.tree.heading(col, text=col)

        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(table_container, orient=tk.VERTICAL,
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Расположение
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Нижняя панель управления тестами
        test_control_frame = ttk.Frame(self)
        test_control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(test_control_frame, text="▶ Запустить текущий",
                   command=self.run_current,
                   width=20).pack(side=tk.LEFT, padx=2)
        ttk.Button(test_control_frame, text="▶▶ Все тесты",
                   command=self.run_all,
                   width=18).pack(side=tk.LEFT, padx=2)
        ttk.Button(test_control_frame, text="Очистить все",
                   command=self.clear_all,
                   width=18).pack(side=tk.RIGHT, padx=2)

        # Привязка событий
        self.tree.bind("<<TreeviewSelect>>", self.on_row_selected)
        self.tree.bind("<Delete>", lambda e: self.delete_test_case())
        self.tree.bind("<Double-1>", self.on_double_click)

        # Настраиваем цвета
        self.tree.tag_configure("success", foreground="green")
        self.tree.tag_configure("error", foreground="red")
        self.tree.tag_configure("pending", foreground="gray")

    def create_test_dialog(self, title: str, initial_case: TestCase = None):
        """Создать диалог для добавления/редактирования теста"""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("400x500")
        dialog.transient(self)
        dialog.grab_set()

        # Переменные для результатов
        self.dialog_result = None

        # Основной фрейм
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Название теста
        ttk.Label(main_frame, text="Название теста:",
                  font=('Arial', 9, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        name_var = tk.StringVar(
            value=initial_case.name if initial_case else f"Тест {len(self.test_suite.test_cases) + 1}")
        name_entry = ttk.Entry(main_frame, textvariable=name_var, width=40)
        name_entry.pack(fill=tk.X, pady=(0, 15))
        name_entry.select_range(0, tk.END)
        name_entry.focus()

        # Разделитель
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Фрейм для прокрутки
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Получаем блоки схемы
        input_blocks = []
        output_blocks = []
        for block_id, block in self.test_suite.circuit.blocks.items():
            if block.type == BlockType.INPUT:
                input_blocks.append((block_id, block.name))
            elif block.type == BlockType.OUTPUT:
                output_blocks.append((block_id, block.name))

        input_vars = {}
        output_vars = {}

        # Входные блоки
        if input_blocks:
            ttk.Label(scrollable_frame, text="Входные значения:",
                      font=('Arial', 9, 'bold')).pack(anchor=tk.W, pady=(0, 10))

            for block_id, block_name in input_blocks:
                frame = ttk.Frame(scrollable_frame)
                frame.pack(fill=tk.X, padx=5, pady=3)

                ttk.Label(frame, text=block_name, width=15,
                          anchor=tk.W).pack(side=tk.LEFT)

                # Получаем начальное значение
                initial_value = False
                if initial_case and block_id in initial_case.inputs:
                    initial_value = initial_case.inputs[block_id]

                var = tk.BooleanVar(value=initial_value)
                input_vars[block_id] = var

                # Чекбокс с динамической надписью
                check = ttk.Checkbutton(
                    frame,
                    text="True" if initial_value else "False",
                    variable=var,
                    width=8
                )
                check.pack(side=tk.LEFT)

                # Обновление текста при изменении
                var.trace_add('write',
                              lambda *args, v=var, cb=check: cb.configure(text="True" if v.get() else "False"))

        # Разделитель
        if input_blocks and output_blocks:
            ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)

        # Выходные блоки
        if output_blocks:
            ttk.Label(scrollable_frame, text="Ожидаемые выходы:",
                      font=('Arial', 9, 'bold')).pack(anchor=tk.W, pady=(0, 10))

            for block_id, block_name in output_blocks:
                frame = ttk.Frame(scrollable_frame)
                frame.pack(fill=tk.X, padx=5, pady=3)

                ttk.Label(frame, text=block_name, width=15,
                          anchor=tk.W).pack(side=tk.LEFT)

                # Получаем начальное значение
                initial_value = False
                if initial_case and block_id in initial_case.expected_outputs:
                    initial_value = initial_case.expected_outputs[block_id]

                var = tk.BooleanVar(value=initial_value)
                output_vars[block_id] = var

                # Чекбокс с динамической надписью
                check = ttk.Checkbutton(
                    frame,
                    text="True" if initial_value else "False",
                    variable=var,
                    width=8
                )
                check.pack(side=tk.LEFT)

                # Обновление текста
                var.trace_add('write',
                              lambda *args, v=var, cb=check: cb.configure(text="True" if v.get() else "False"))

        # Если нет блоков
        if not input_blocks and not output_blocks:
            ttk.Label(scrollable_frame, text="Нет входных/выходных блоков в схеме",
                      foreground="gray", font=('Arial', 9)).pack(pady=20)

        # Упаковываем canvas и scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Кнопки внизу диалога - ВОТ ЭТО ВАЖНО!
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))

        def on_ok():
            name = name_var.get().strip()
            if not name:
                name = f"Тест {len(self.test_suite.test_cases) + 1}"

            inputs = {block_id: var.get() for block_id, var in input_vars.items()}
            expected_outputs = {block_id: var.get() for block_id, var in output_vars.items()}

            self.dialog_result = (name, inputs, expected_outputs)
            dialog.destroy()

        def on_cancel():
            self.dialog_result = None
            dialog.destroy()

        # Кнопка "Добавить" (или "Сохранить" при редактировании)
        btn_text = "Сохранить" if initial_case else "Добавить"
        ttk.Button(button_frame, text=btn_text, command=on_ok,
                   width=10).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Отмена", command=on_cancel,
                   width=10).pack(side=tk.RIGHT)

        # Центрируем диалог
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')

        # Ждем закрытия диалога
        self.wait_window(dialog)

        return self.dialog_result

    def add_test_case_dialog(self):
        """Диалог добавления нового тестового случая"""
        if not self.test_suite.circuit.blocks:
            messagebox.showwarning("Внимание",
                                 "Нет схемы. Добавьте блоки INPUT/OUTPUT перед созданием тестов.")
            return

        result = self.create_test_dialog("Добавить тестовый случай")
        if result:
            name, inputs, expected_outputs = result
            self.test_suite.add_test_case(name, inputs, expected_outputs)
            self.refresh_table()

    def edit_test_case(self):
        """Редактировать выбранный тестовый случай"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите тестовый случай для редактирования")
            return

        case_id = selection[0]
        case = None
        for test_case in self.test_suite.test_cases:
            if test_case.id == case_id:
                case = test_case
                break

        if not case:
            return

        result = self.create_test_dialog("Редактировать тестовый случай", case)
        if result:
            name, inputs, expected_outputs = result
            self.test_suite.update_test_case(case_id, name=name,
                                           inputs=inputs,
                                           expected_outputs=expected_outputs)
            self.refresh_table()

    def refresh_table(self):
        """Обновить таблицу"""
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Заполняем данными
        for i, case in enumerate(self.test_suite.test_cases):
            # Форматируем входы
            inputs_str = self._format_inputs(case.inputs)

            # Форматируем ожидаемые выходы
            outputs_str = self._format_outputs(case.expected_outputs)

            # Результат
            result, tags = self._get_result_info(case.passed)

            self.tree.insert("", tk.END,
                             values=(i + 1, case.name, inputs_str,
                                     outputs_str, result),
                             tags=tags,
                             iid=case.id)

        # Автоподбор ширины колонок
        self.auto_size_columns()

    def _format_inputs(self, inputs: Dict[str, bool]) -> str:
        """Форматировать входные значения"""
        if not inputs:
            return "нет"

        formatted = []
        for block_id, value in inputs.items():
            block = self.test_suite.circuit.blocks.get(block_id)
            if block:
                val_str = "1" if value else "0"
                formatted.append(f"{block.name}={val_str}")

        return ", ".join(formatted) if formatted else ""

    def _format_outputs(self, outputs: Dict[str, bool]) -> str:
        """Форматировать выходные значения"""
        if not outputs:
            return "нет"

        formatted = []
        for block_id, value in outputs.items():
            block = self.test_suite.circuit.blocks.get(block_id)
            if block:
                val_str = "1" if value else "0"
                formatted.append(f"{block.name}={val_str}")

        return ", ".join(formatted) if formatted else ""

    def _get_result_info(self, passed: bool) -> tuple:
        """Получить информацию о результате теста"""
        if passed is True:
            return "✓ Успех", ("success",)
        elif passed is False:
            return "✗ Ошибка", ("error",)
        else:
            return "○ Не запущен", ("pending",)

    def auto_size_columns(self):
        """Автоподбор ширины колонок"""
        for col in self.tree["columns"]:
            max_width = 100
            for item in self.tree.get_children():
                value = self.tree.set(item, col)
                if value:
                    width = len(value) * 8 + 20
                    if width > max_width:
                        max_width = min(width, 300)
            self.tree.column(col, width=max_width)

    def delete_test_case(self):
        """Удалить выбранный тестовый случай"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите тестовый случай для удаления")
            return

        if messagebox.askyesno("Подтверждение",
                             "Удалить выбранный тестовый случай?"):
            case_id = selection[0]
            self.test_suite.delete_test_case(case_id)
            self.refresh_table()

    def clear_all(self):
        """Очистить все тестовые случаи"""
        if not self.test_suite.test_cases:
            return

        if messagebox.askyesno("Подтверждение",
                             "Очистить все тестовые случаи?"):
            self.test_suite.test_cases.clear()
            self.test_suite.current_case_index = -1
            self.refresh_table()

    def on_row_selected(self, event=None):
        """Обработка выбора строки"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            index = int(item['values'][0]) - 1
            self.test_suite.set_current_case(index)

            if self.on_case_selected:
                self.on_case_selected(index)

    def on_double_click(self, event):
        """Обработка двойного клика - запуск теста"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            index = int(item['values'][0]) - 1
            self.test_suite.set_current_case(index)

            if self.on_case_selected:
                self.on_case_selected(index, run_test=True)

    def run_current(self):
        """Запустить текущий тестовый случай"""
        if self.test_suite.current_case_index >= 0:
            if self.on_case_selected:
                self.on_case_selected(self.test_suite.current_case_index, run_test=True)
        else:
            messagebox.showwarning("Внимание", "Сначала выберите тестовый случай")

    def run_all(self):
        """Запустить все тестовые случаи и выполнить полный анализ"""
        if not self.test_suite.test_cases:
            messagebox.showwarning("Внимание", "Нет тестовых случаев для запуска")
            return

        # Сохраняем текущий выбранный тест
        original_index = self.test_suite.current_case_index

        print(f"\n{'=' * 60}")
        print("ЗАПУСК ВСЕХ ТЕСТОВ")
        print(f"{'=' * 60}")

        # Прогоняем все тесты
        for i in range(len(self.test_suite.test_cases)):
            print(f"\n--- Тест {i + 1}/{len(self.test_suite.test_cases)} ---")
            self.test_suite.set_current_case(i)
            if self.on_case_selected:
                self.on_case_selected(i, run_test=True)

        # Восстанавливаем оригинальный выбор
        if original_index >= 0:
            self.test_suite.set_current_case(original_index)
            self.tree.selection_set(self.get_item_id(original_index))

        # ВЫПОЛНЯЕМ АНАЛИЗ DO-178C Level A автоматически
        if self.app_reference and hasattr(self.app_reference, 'analyzer'):
            print(f"\n{'=' * 60}")
            print("АВТОМАТИЧЕСКИЙ АНАЛИЗ DO-178C Level A")
            print(f"{'=' * 60}")

            try:
                # Запускаем анализ DO-178C Level A
                results = self.app_reference.analyzer.run_level_a_analysis(
                    self.app_reference.test_suite,
                    self.app_reference.simulator
                )

                print(f"✅ DO-178C Level A анализ завершен!")
                print(f"   Соответствует Level A: {results['statistics']['level_a_percentage']:.1f}%")
                print(f"   Branch Coverage: {results['statistics']['branch_coverage_percentage']:.1f}%")

                # Обновляем панель покрытия
                if hasattr(self.app_reference, 'coverage_panel'):
                    # Принудительно обновляем все данные
                    self.app_reference.coverage_panel.update_coverage()
                    if hasattr(self.app_reference.analyzer, 'decision_mcdc_results'):
                        # Обновляем таблицы MC/DC
                        results = self.app_reference.analyzer.decision_mcdc_results
                        self.app_reference.coverage_panel.update_mcdc_table(results.get('block_statuses', {}))
                        self.app_reference.coverage_panel.update_level_a_stats()
                    # Переключаемся на вкладку DO-178C Level A
                    self.app_reference.coverage_panel.notebook.select(2)  # 3-я вкладка

                # Показываем краткое уведомление
                level_a_status = self.app_reference.analyzer.get_level_a_status()
                if level_a_status['compliant']:
                    messagebox.showinfo(
                        "Анализ DO-178C Level A завершен",
                        f"✅ Схема соответствует DO-178C Level A!\n\n"
                        f"• Покрыто блоков: {level_a_status['blocks_level_a']}/{level_a_status['blocks_total']}\n"
                        f"• Процент покрытия: {level_a_status['percentage']:.1f}%"
                    )
                else:
                    messagebox.showwarning(
                        "Анализ DO-178C Level A завершен",
                        f"⚠️ Схема НЕ соответствует DO-178C Level A\n\n"
                        f"• Покрыто блоков: {level_a_status['blocks_level_a']}/{level_a_status['blocks_total']}\n"
                        f"• Процент покрытия: {level_a_status['percentage']:.1f}%\n\n"
                        f"Подробности см. во вкладке 'DO-178C Level A'"
                    )

            except Exception as e:
                print(f"Ошибка при анализе DO-178C: {e}")
                import traceback
                traceback.print_exc()
                messagebox.showerror("Ошибка анализа",
                                     f"Ошибка при анализе DO-178C Level A:\n{str(e)}")

        self.refresh_table()

    def get_item_id(self, index: int) -> str:
        """Получить ID элемента Treeview по индексу"""
        if 0 <= index < len(self.test_suite.test_cases):
            return self.test_suite.test_cases[index].id
        return ""