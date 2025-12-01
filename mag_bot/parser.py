import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dataclasses import dataclass
import time

@dataclass
class Discipline:
    __slots__ = ("name", "hours", "controls")
    name: str
    hours: list
    controls: list

    @property
    def has_hours(self):
        return any(h not in ["0", ""] for h in self.hours)

    @property
    def control_type(self):
        if self.controls[0] == "+":
            return "Экзамен"
        elif self.controls[1] == "+":
            return "Зачёт"
        return None

def log(msg):
    print(f"→ {msg}")

def parse_plan(login: str, password: str, semester: int):
    """Парсинг учебного плана, сохранение и загрузка из data.json с pandas"""
    json_file = "data/data.json"
    df = pd.DataFrame()

    # Загружаем JSON в DataFrame
    if os.path.exists(json_file):
        try:
            df = pd.read_json(json_file, encoding="utf-8")
        except ValueError:
            log("Файл data.json пустой или повреждён, создаём новый")
            df = pd.DataFrame()

    # Проверяем кэш по логину и семестру
    if not df.empty:
        cached = df[(df['semester'] == semester) & (df['login'] == login)]
        if not cached.empty:
            log(f"Семестр {semester} для пользователя {login} уже есть в файле, загружаем из JSON")
            return cached.to_dict(orient="records")

    # Если нет — парсим новый
    log("Запуск парсера...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    wait = WebDriverWait(driver, 30)
    new_data = []

    try:
        log("Открываем сайт kpfu.ru")
        driver.get("https://kpfu.ru")
        driver.maximize_window()

        log("Входим в ЛК")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.lk-link"))).click()
        wait.until(EC.presence_of_element_located((By.NAME, "p_login"))).send_keys(login)
        driver.find_element(By.NAME, "p_pass").send_keys(password)
        driver.find_element(By.XPATH, "//input[@value='Отправить']").click()

        time.sleep(3)
        log("Переходим на учебный план")
        driver.get("https://newlk.kpfu.ru/services/session/curriculum")
        time.sleep(2)

        if semester in [3, 4]:
            try:
                wait.until(EC.element_to_be_clickable((
                    By.XPATH,
                    "//label[contains(@class, 'ant-radio-button-wrapper') and contains(., '2-й курс')]"
                ))).click()
                time.sleep(2)
                log("Переключились на 2 курс")
            except:
                log("Не удалось переключиться на 2 курс")

        table_body = wait.until(EC.presence_of_element_located((By.XPATH, "//table/tbody")))
        rows = table_body.find_elements(By.TAG_NAME, "tr")

        def get_cells_by_semester(cells, sem):
            if sem in [1, 3]:
                return cells[9:14]
            if sem in [2, 4]:
                return cells[14:19]
            return []

        log("Начинаем разбор таблицы")
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue
            name = cells[0].text.strip()
            if not name:
                continue
            sem_cells = get_cells_by_semester(cells, semester)
            data_cells = [c.text.strip() for c in sem_cells]
            if len(data_cells) < 5:
                continue
            hours = data_cells[0:3]
            controls = data_cells[3:5]
            disc = Discipline(name=name, hours=hours, controls=controls)
            if disc.has_hours and disc.control_type:
                hours_sum = sum(int(h) for h in disc.hours if h.isdigit())
                item = {
                    "name": disc.name,
                    "hours": hours_sum,
                    "type": disc.control_type,
                    "semester": semester,
                    "login": login
                }
                new_data.append(item)
                log(f"Добавлено: {disc.name} — {disc.control_type} ({hours_sum} ч.)")

    finally:
        driver.quit()
        log("Парсер завершил работу")

    # Объединяем с существующими данными
    df_new = pd.DataFrame(new_data)
    if not df.empty:
        df = df[~((df['semester'] == semester) & (df['login'] == login))]
        df = pd.concat([df, df_new], ignore_index=True)
    else:
        df = df_new

    df.to_json(json_file, orient="records", force_ascii=False, indent=4)
    log("Файл data.json успешно обновлён")

    return new_data
