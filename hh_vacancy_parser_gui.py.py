import requests
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import Counter
import tkinter as tk
from tkinter import ttk
import webbrowser
import time

# Настройки API HeadHunter
BASE_URL = "https://api.hh.ru/vacancies"
HEADERS = {"User-Agent": "api-test-agent"}
PARAMS = {
    "text": "Python OR Java",  # Поиск по ключевым словам
    "area": 1,  # Москва
    "per_page": 100,  # Вакансий на страницу
    "page": 0  # Начальная страница
}

def fetch_vacancies():
    """Получение данных о вакансиях с API HeadHunter"""
    vacancies = []
    page = 0
    while True:
        response = requests.get(BASE_URL, headers=HEADERS, params={**PARAMS, "page": page})
        if response.status_code != 200:
            print(f"Ошибка API: {response.status_code}")
            break
        
        data = response.json()
        vacancies.extend(data.get("items", []))
        
        if page >= data.get("pages", 0) - 1:
            break
            
        page += 1
        time.sleep(0.5)
    
    return vacancies

def extract_skills(vacancy):
    """Извлечение навыков из описания вакансии"""
    skills = []
    if vacancy.get("snippet", {}).get("requirement"):
        description = vacancy["snippet"]["requirement"].lower()
        common_skills = ["python", "java", "sql", "git", "docker", "javascript", 
                        "linux", "aws", "postgresql", "mysql"]
        for skill in common_skills:
            if skill in description:
                skills.append(skill)
    
    if vacancy.get("key_skills"):
        skills.extend([skill["name"].lower() for skill in vacancy["key_skills"]])
    
    return skills

def analyze_skills(vacancies):
    """Анализ топ-5 востребованных навыков"""
    all_skills = []
    for vacancy in vacancies:
        skills = extract_skills(vacancy)
        all_skills.extend(skills)
    
    skill_counts = Counter(all_skills)
    top_skills = skill_counts.most_common(5)
    
    return top_skills

def save_to_csv(vacancies, top_skills):
    """Сохранение данных в CSV"""
    vacancy_data = [{
        "id": v["id"],
        "name": v["name"],
        "company": v.get("employer", {}).get("name", ""),
        "salary": v.get("salary", {}).get("from", None) if v.get("salary") else None,
        "url": v.get("alternate_url", ""),
        "skills": ", ".join(extract_skills(v)),
        "employment": v.get("employment", {}).get("name", "N/A") if v.get("employment") else "N/A"
    } for v in vacancies]
    
    df_vacancies = pd.DataFrame(vacancy_data)
    df_skills = pd.DataFrame(top_skills, columns=["Skill", "Count"])
    
    df_vacancies.to_csv("vacancies.csv", index=False, encoding="utf-8")
    df_skills.to_csv("top_skills.csv", index=False, encoding="utf-8")
    print("Данные сохранены в vacancies.csv и top_skills.csv")

def create_gui(vacancies, top_skills):
    """Создание GUI с диаграммой и таблицей вакансий"""
    root = tk.Tk()
    root.title("Анализ вакансий HeadHunter")
    root.geometry("1200x700")

    # Фрейм для диаграммы
    chart_frame = tk.Frame(root)
    chart_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=False)

    # Создание диаграммы
    fig, ax = plt.subplots(figsize=(6, 4))
    skills, counts = zip(*top_skills)
    ax.bar(skills, counts, color=['#36A2EB', '#FF6384', '#FFCE56', '#4BC0C0', '#9966FF'])
    ax.set_title("Топ-5 востребованных навыков")
    ax.set_xlabel("Навыки")
    ax.set_ylabel("Количество упоминаний")
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    for i, count in enumerate(counts):
        ax.text(i, count + 10, str(count), ha='center', va='bottom')
    plt.tight_layout()

    # Встраивание диаграммы
    canvas = FigureCanvasTkAgg(fig, master=chart_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # Фрейм для фильтров
    filter_frame = tk.Frame(root)
    filter_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

    # Фильтр по типу работы
    tk.Label(filter_frame, text="Тип занятости:").pack(side=tk.LEFT, padx=5)
    employment_var = tk.StringVar(value="Все")
    employment_options = ["Все", "Полная занятость", "Частичная занятость", "Проектная работа", "Стажировка", "Волонтёрство"]
    employment_menu = ttk.Combobox(filter_frame, textvariable=employment_var, values=employment_options, state="readonly")
    employment_menu.pack(side=tk.LEFT, padx=5)

    # Фрейм для таблицы
    table_frame = tk.Frame(root)
    table_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

    # Создание таблицы
    tree = ttk.Treeview(table_frame, columns=("ID", "Name", "Company", "Salary", "Employment", "URL"), show="headings")
    tree.heading("ID", text="ID")
    tree.heading("Name", text="Название")
    tree.heading("Company", text="Компания")
    tree.heading("Salary", text="Зарплата")
    tree.heading("Employment", text="Тип занятости")
    tree.heading("URL", text="Ссылка")
    tree.column("ID", width=50)
    tree.column("Name", width=300)
    tree.column("Company", width=200)
    tree.column("Salary", width=100)
    tree.column("Employment", width=150)
    tree.column("URL", width=300)

    # Скроллбары
    y_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    x_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscroll=y_scrollbar.set, xscroll=x_scrollbar.set)
    y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
    tree.pack(fill=tk.BOTH, expand=True)

    def update_table(filter_employment="Все"):
        """Обновление таблицы с учётом фильтра"""
        for item in tree.get_children():
            tree.delete(item)
        
        for v in vacancies:
            employment = v.get("employment", {}).get("name", "N/A") if v.get("employment") else "N/A"
            if filter_employment == "Все" or employment == filter_employment:
                salary = v.get("salary", {}).get("from", "N/A") if v.get("salary") else "N/A"
                tree.insert("", tk.END, values=(
                    v["id"],
                    v["name"],
                    v.get("employer", {}).get("name", "N/A"),
                    salary,
                    employment,
                    v.get("alternate_url", "N/A")
                ))

    # Изначальное заполнение таблицы
    update_table()

    # Обработчик изменения фильтра
    def apply_filter(*args):
        update_table(employment_var.get())

    employment_var.trace("w", apply_filter)

    # Обработчик клика по ссылке
    def on_tree_select(event):
        selected_item = tree.selection()
        if selected_item:
            item = tree.item(selected_item)
            url = item["values"][5]  # Колонка URL
            if url and url != "N/A":
                webbrowser.open(url)

    tree.bind("<Double-1>", on_tree_select)

    root.mainloop()

def main():
    print("Сбор данных о вакансиях...")
    vacancies = fetch_vacancies()
    print(f"Собрано {len(vacancies)} вакансий")
    
    print("Анализ навыков...")
    top_skills = analyze_skills(vacancies)
    print("Топ-5 навыков:", top_skills)
    
    print("Сохранение результатов...")
    save_to_csv(vacancies, top_skills)
    
    print("Запуск GUI...")
    create_gui(vacancies, top_skills)
    print("Готово!")

if __name__ == "__main__":
    main()