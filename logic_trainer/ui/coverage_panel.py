"""
Панель анализа покрытия с поддержкой DO-178C Level A
Исправленная терминология согласно DO-178C:
- Decision Coverage = покрытие решений (True/False)
- Branch Coverage = покрытие условий (входов блока)
- MC/DC = Modified Condition/Decision Coverage
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional
from logic_trainer.core.coverage import CoverageAnalyzer


class CoveragePanel(ttk.Frame):
    """Панель анализа покрытия по DO-178C"""

    def __init__(self, parent, coverage_analyzer: CoverageAnalyzer,
                 test_suite, simulator, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.analyzer = coverage_analyzer
        self.test_suite = test_suite
        self.simulator = simulator

        self.setup_ui()
        self.update_coverage()

    def setup_ui(self):
        """Настроить интерфейс панели покрытия"""
        # Заголовок
        title = ttk.Label(
            self,
            text="Анализ покрытия по DO-178C",
            font=('Arial', 11, 'bold')
        )
        title.pack(pady=10)

        # Описание
        desc = ttk.Label(
            self,
            text="DO-178C Level A требует 100% MC/DC покрытие.\n"
                 "MC/DC = каждая ветка решения и каждое условие независимо влияет на выход.",
            font=('Arial', 9),
            justify=tk.LEFT,
            foreground='gray'
        )
        desc.pack(pady=(0, 15), padx=10)

        # Основная статистика
        self.stats_frame = ttk.Frame(self)
        self.stats_frame.pack(fill=tk.X, padx=10, pady=5)

        # Переменные для статистики
        self.decision_var = tk.StringVar(value="0%")  # Decision Coverage (True/False)
        self.mcdc_var = tk.StringVar(value="0%")      # MC/DC покрытие
        self.level_a_var = tk.StringVar(value="0%")   # DO-178C Level A
        self.status_var = tk.StringVar(value="НЕ АНАЛИЗИРОВАНО")

        # Создаем метки статистики
        self._create_stat_label("Decision Coverage:", self.decision_var, 0, 0)
        self._create_stat_label("MC/DC покрытие:", self.mcdc_var, 0, 1)
        self._create_stat_label("DO-178C Level A:", self.level_a_var, 1, 0)

        # Статус
        ttk.Label(self.stats_frame, text="Статус:",
                 font=('Arial', 9)).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        self.status_label = ttk.Label(self.stats_frame, textvariable=self.status_var,
                                    font=('Arial', 9, 'bold'))
        self.status_label.grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=2)

        # Прогресс-бары
        ttk.Label(self, text="Decision Coverage (True/False):").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.decision_progress = ttk.Progressbar(self, length=200, mode='determinate')
        self.decision_progress.pack(fill=tk.X, padx=10, pady=(0, 5))

        ttk.Label(self, text="MC/DC покрытие условий:").pack(anchor=tk.W, padx=10, pady=(5, 0))
        self.mcdc_progress = ttk.Progressbar(self, length=200, mode='determinate')
        self.mcdc_progress.pack(fill=tk.X, padx=10, pady=(0, 5))

        ttk.Label(self, text="DO-178C Level A:").pack(anchor=tk.W, padx=10, pady=(5, 0))
        self.level_a_progress = ttk.Progressbar(self, length=200, mode='determinate')
        self.level_a_progress.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Кнопки управления
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(
            btn_frame,
            text="Обновить покрытие",
            command=lambda: self.update_coverage(),
            width=18
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_frame,
            text="Проверить Level A",
            command=self.check_level_a_compliance,
            width=18
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_frame,
            text="Экспорт отчета",
            command=self.export_level_a_report,
            width=18
        ).pack(side=tk.RIGHT, padx=2)

        # Разделитель
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)

        # Notebook для разных видов покрытия
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Вкладка 1: Decision Coverage (True/False)
        self.decision_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.decision_tab, text="Decision Coverage")
        self.setup_decision_tab()

        # Вкладка 2: MC/DC (Branch Coverage)
        self.mcdc_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.mcdc_tab, text="MC/DC (Branch)")
        self.setup_mcdc_tab()

        # Вкладка 3: DO-178C Level A
        self.level_a_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.level_a_tab, text="DO-178C Level A")
        self.setup_level_a_tab()

    def _create_stat_label(self, text, var, row, col):
        """Создать метку статистики"""
        frame = ttk.Frame(self.stats_frame)
        frame.grid(row=row, column=col*2, sticky=tk.W, padx=5, pady=2)

        ttk.Label(frame, text=text, font=('Arial', 9)).pack(side=tk.LEFT)
        ttk.Label(frame, textvariable=var, font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=(5, 0))

    def setup_decision_tab(self):
        """Настроить вкладку Decision Coverage (True/False)"""
        # Контейнер для таблицы
        container = ttk.Frame(self.decision_tab)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Дерево для отображения веток
        columns = ("Блок", "Тип", "TRUE", "FALSE", "Статус")
        self.decision_tree = ttk.Treeview(container, columns=columns,
                                         show="headings", height=10)

        # Настройка колонок
        self.decision_tree.column("Блок", width=120)
        self.decision_tree.column("Тип", width=80)
        self.decision_tree.column("TRUE", width=60, anchor=tk.CENTER)
        self.decision_tree.column("FALSE", width=60, anchor=tk.CENTER)
        self.decision_tree.column("Статус", width=100)

        for col in columns:
            self.decision_tree.heading(col, text=col)

        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL,
                                 command=self.decision_tree.yview)
        self.decision_tree.configure(yscrollcommand=scrollbar.set)

        self.decision_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_mcdc_tab(self):
        """Настроить вкладку MC/DC (Branch Coverage)"""
        # Контейнер для таблицы
        container = ttk.Frame(self.mcdc_tab)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Дерево для отображения MC/DC статуса
        columns = ("Блок", "Тип", "Входы MC/DC", "Ветки", "Статус MC/DC")
        self.mcdc_tree = ttk.Treeview(container, columns=columns,
                                     show="headings", height=10)

        # Настройка колонок
        self.mcdc_tree.column("Блок", width=120)
        self.mcdc_tree.column("Тип", width=80)
        self.mcdc_tree.column("Входы MC/DC", width=100, anchor=tk.CENTER)
        self.mcdc_tree.column("Ветки", width=80, anchor=tk.CENTER)
        self.mcdc_tree.column("Статус MC/DC", width=120)

        for col in columns:
            self.mcdc_tree.heading(col, text=col)

        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL,
                                 command=self.mcdc_tree.yview)
        self.mcdc_tree.configure(yscrollcommand=scrollbar.set)

        self.mcdc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_level_a_tab(self):
        """Настроить вкладку DO-178C Level A"""
        # Контейнер
        container = ttk.Frame(self.level_a_tab)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Текстовое поле для детального отчета
        text_frame = ttk.Frame(container)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.level_a_text = tk.Text(text_frame, wrap=tk.WORD,
                                   font=('Courier', 9), height=15)
        scrollbar = ttk.Scrollbar(text_frame, command=self.level_a_text.yview)
        self.level_a_text.configure(yscrollcommand=scrollbar.set)

        self.level_a_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def update_coverage(self, block_states: Dict[str, Optional[bool]] = None):
        """Обновить информацию о покрытии"""
        try:
            # Если переданы состояния блоков - обновляем покрытие
            if block_states is not None:
                self.analyzer.calculate_current_coverage(block_states)

            # Обновляем Decision Coverage статистику
            total_branches = self.analyzer.calculate_total_branches()
            covered_branches = len(self.analyzer.get_covered_branches())
            decision_percentage = self.analyzer.get_coverage_percentage()

            self.decision_var.set(f"{decision_percentage:.1f}%")
            self.decision_progress['value'] = decision_percentage

            # Обновляем таблицу Decision Coverage
            self.update_decision_table()

            # Если есть результаты Decision MC/DC
            if hasattr(self.analyzer, 'decision_mcdc_results') and self.analyzer.decision_mcdc_results:
                self.update_mcdc_stats()
                self.update_level_a_stats()
            else:
                # Сбрасываем значения
                self.mcdc_var.set("0%")
                self.mcdc_progress['value'] = 0
                self.level_a_var.set("0%")
                self.level_a_progress['value'] = 0
                self.status_var.set("НЕ АНАЛИЗИРОВАНО")
                self.status_label.config(foreground="black")

        except Exception as e:
            print(f"Ошибка при обновлении покрытия: {e}")
            import traceback
            traceback.print_exc()

    def update_decision_table(self):
        """Обновить таблицу Decision Coverage (True/False)"""
        # Очищаем таблицу
        for item in self.decision_tree.get_children():
            self.decision_tree.delete(item)

        # Собираем информацию по блокам
        covered_branches = self.analyzer.get_covered_branches()

        # Для каждого не-входного блока
        for block_id, block in self.analyzer.circuit.blocks.items():
            if block.type.value in ['AND', 'OR', 'NOT', 'XOR', 'NAND', 'NOR', 'OUTPUT']:
                # Проверяем ветки True/False
                true_covered = (block_id, True) in covered_branches
                false_covered = (block_id, False) in covered_branches

                # Определяем статус Decision Coverage
                if true_covered and false_covered:
                    status = "FULL"
                    status_color = "green"
                elif true_covered or false_covered:
                    status = "PARTIAL"
                    status_color = "orange"
                else:
                    status = "NONE"
                    status_color = "red"

                # Добавляем в таблицу
                item_id = self.decision_tree.insert("", tk.END, values=(
                    block.name,
                    block.type.value,
                    "✓" if true_covered else "✗",
                    "✓" if false_covered else "✗",
                    status
                ))

                # Цвет статуса
                self.decision_tree.item(item_id, tags=(status.lower(),))

        # Настройка цветов тегов
        self.decision_tree.tag_configure("full", foreground="green")
        self.decision_tree.tag_configure("partial", foreground="orange")
        self.decision_tree.tag_configure("none", foreground="red")

    def update_mcdc_stats(self):
        """Обновить статистику MC/DC"""
        if not self.analyzer.decision_mcdc_results:
            return

        results = self.analyzer.decision_mcdc_results
        stats = results.get('statistics', {})

        # Обновляем MC/DC статистику
        mcdc_percentage = stats.get('partial_mcdc_percentage', 0)
        self.mcdc_var.set(f"{mcdc_percentage:.1f}%")
        self.mcdc_progress['value'] = mcdc_percentage

        # Обновляем таблицу MC/DC
        self.update_mcdc_table(results.get('block_statuses', {}))

    def update_mcdc_table(self, block_statuses: Dict):
        """Обновить таблицу MC/DC"""
        # Очищаем таблицу
        for item in self.mcdc_tree.get_children():
            self.mcdc_tree.delete(item)

        # Заполняем данными
        for block_id, status in block_statuses.items():
            # Подсчитываем покрытые входы (conditions)
            covered_inputs = sum(1 for covered in status.input_status.values() if covered)
            total_inputs = len(status.input_status)

            # Проверяем ветки True/False (decisions)
            has_true = status.has_true_branch
            has_false = status.has_false_branch

            # Определяем статус MC/DC
            if status.all_inputs_covered and has_true and has_false:
                mcdc_status = "Level A ✓"
                tag = "level_a"
            elif covered_inputs > 0:
                mcdc_status = f"MC/DC {covered_inputs}/{total_inputs}"
                tag = "partial"
            else:
                mcdc_status = "No MC/DC"
                tag = "none"

            # Форматируем ветки
            branches = f"{'T' if has_true else '_'}{'F' if has_false else '_'}"

            # Добавляем в таблицу
            item_id = self.mcdc_tree.insert("", tk.END, values=(
                status.block_name,
                status.block_type.value,
                f"{covered_inputs}/{total_inputs}",
                branches,
                mcdc_status
            ))

            # Цвет статуса
            self.mcdc_tree.item(item_id, tags=(tag,))

        # Настройка цветов тегов
        self.mcdc_tree.tag_configure("level_a", foreground="green")
        self.mcdc_tree.tag_configure("partial", foreground="orange")
        self.mcdc_tree.tag_configure("none", foreground="red")

    def update_level_a_stats(self):
        """Обновить статистику DO-178C Level A"""
        if not self.analyzer.decision_mcdc_results:
            print("NOPE(update_level_a_stats)")
            return

        results = self.analyzer.decision_mcdc_results
        stats = results.get('statistics', {})

        # Обновляем Level A статистику
        level_a_percentage = stats.get('level_a_percentage', 0)
        self.level_a_var.set(f"{level_a_percentage:.1f}%")
        self.level_a_progress['value'] = level_a_percentage

        # Обновляем статус
        if level_a_percentage == 100:
            self.status_var.set("✓ СООТВЕТСТВУЕТ")
            self.status_label.config(foreground="green")
        else:
            self.status_var.set("✗ НЕ СООТВЕТСТВУЕТ")
            self.status_label.config(foreground="red")

        # Обновляем текстовый отчет
        self.update_level_a_report(results.get('report', ''))

    def update_level_a_report(self, report: str):
        """Обновить текстовый отчет Level A"""
        print(f"Обновление отчета Level A, длина: {len(report) if report else 0}")

        if not hasattr(self, 'level_a_text') or self.level_a_text is None:
            print("ERROR: level_a_text не существует!")
            return

        print(f'{report=}')

        # ВАЖНО: Временно разблокируем для редактирования
        self.level_a_text.config(state=tk.NORMAL)

        self.level_a_text.delete(1.0, tk.END)
        if report:
            print(f"Вставляем отчет в level_a_text")
            self.level_a_text.insert(tk.END, report)
        else:
            print("Вставляем сообщение об отсутствии анализа")
            self.level_a_text.insert(tk.END, "DO-178C Level A анализ не выполнен...")

        # Снова блокируем
        self.level_a_text.config(state=tk.DISABLED)

        # ПРИНУДИТЕЛЬНО ОБНОВЛЯЕМ ВИДЖЕТ
        self.level_a_text.update_idletasks()

        print("Отчет обновлен")

    def check_level_a_compliance(self):
        """Проверить соответствие DO-178C Level A"""
        # Проверяем, выполнен ли анализ
        if not hasattr(self.analyzer, 'decision_mcdc_results') or not self.analyzer.decision_mcdc_results:
            messagebox.showinfo(
                "DO-178C Level A",
                "Анализ DO-178C Level A не выполнен.\n\n"
                "Для выполнения анализа:\n"
                "1. Создайте тестовые случаи\n"
                "2. Нажмите '▶▶ Все тесты' на вкладке 'Тесты'\n"
                "3. Анализ выполнится автоматически"
            )
            return

        status = self.analyzer.get_level_a_status()

        if status['compliant']:
            messagebox.showinfo(
                "DO-178C Level A",
                f"✅ Схема соответствует DO-178C Level A!\n\n"
                f"• Покрыто блоков: {status['blocks_level_a']}/{status['blocks_total']}\n"
                f"• Процент покрытия: {status['percentage']:.1f}%\n\n"
                f"Все требования MC/DC выполнены:\n"
                f"• Каждая ветка решения (True/False) покрыта\n"
                f"• Каждое условие независимо влияет на решение"
            )
        else:
            # Получаем детали по непокрытым блокам
            uncovered_info = self.get_uncovered_blocks_info()

            messagebox.showwarning(
                "DO-178C Level A",
                f"❌ Схема НЕ соответствует DO-178C Level A\n\n"
                f"• Покрыто блоков: {status['blocks_level_a']}/{status['blocks_total']}\n"
                f"• Процент покрытия: {status['percentage']:.1f}%\n\n"
                f"Основные проблемы:\n{uncovered_info}"
            )

    def get_uncovered_blocks_info(self) -> str:
        """Получить информацию о непокрытых блоках"""
        if not self.analyzer.decision_mcdc_results:
            return "Данные анализа отсутствуют"

        results = self.analyzer.decision_mcdc_results
        block_statuses = results.get('block_statuses', {})

        uncovered = []
        for status in block_statuses.values():
            if not (status.all_inputs_covered and status.has_true_branch and status.has_false_branch):
                issues = []
                if not status.has_true_branch:
                    issues.append("нет TRUE ветки")
                if not status.has_false_branch:
                    issues.append("нет FALSE ветки")

                # Непокрытые входы
                uncovered_inputs = []
                for input_id, covered in status.input_status.items():
                    if not covered:
                        # Пытаемся получить имя блока
                        input_block = self.analyzer.circuit.blocks.get(input_id)
                        if input_block:
                            uncovered_inputs.append(input_block.name)

                if uncovered_inputs:
                    issues.append(f"входы без MC/DC: {', '.join(uncovered_inputs[:3])}")

                if issues:
                    uncovered.append(f"• {status.block_name}: {', '.join(issues)}")

        if uncovered:
            return "\n".join(uncovered[:5])  # Показываем первые 5
        else:
            return "Все блоки покрыты!"

    def export_level_a_report(self):
        """Экспортировать отчет DO-178C Level A"""
        from tkinter import filedialog
        import os

        if not hasattr(self.analyzer, 'decision_mcdc_results') or not self.analyzer.decision_mcdc_results:
            messagebox.showwarning("Внимание", "Сначала выполните анализ DO-178C")
            return

        filename = filedialog.asksaveasfilename(
            title="Экспорт отчета DO-178C",
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )

        if filename:
            try:
                report = self.analyzer.get_decision_mcdc_report()
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(report)

                messagebox.showinfo("Успех", f"Отчет сохранен:\n{os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить отчет: {str(e)}")