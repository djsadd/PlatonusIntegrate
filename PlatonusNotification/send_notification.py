import os
from typing import Any, Dict, List, Optional

from playwright.sync_api import sync_playwright, TimeoutError


def fetch_notifications(
    username: str, password: str, iin: Optional[str] = None, code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Логинится в Platonus, ищет студента по ИИН,
    переходит на детальную страницу и возвращает HTML + данные строки.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(60000)

        # Идём на страницу писем (нас перекинет на логин)
        page.goto("https://platonus.tau-edu.kz/mail?type=1", wait_until="domcontentloaded")

        try:
            page.wait_for_selector("#login_input")
            page.fill("#login_input", username)
            page.fill("#pass_input", password)
        except TimeoutError as exc:
            browser.close()
            raise RuntimeError(
                "Не удалось найти поля логина/пароля на странице авторизации."
            ) from exc

        page.click("#Submit1")
        page.wait_for_load_state("networkidle")

        if not iin:
            browser.close()
            raise RuntimeError("ИИН не передан, поиск студента невозможен.")

        # Переходим на поиск студентов по ИИН
        search_url = (
            "https://platonus.tau-edu.kz/template.html#/students"
            f"?page=1&countInPart=30&search={iin}"
            "&facultyID=0&gender=0&fundingProgram=0&participantProgram=0"
            "&year=0&cafedraID=0&professionID=0&specializationID=0&sGroupID=0"
            "&course=0&studyFormID=0&departmentID=0&state=1&academic_mobility=0"
            "&studyLanguageID=0&paymentFormID=0&militaryID=0&conditionally_enrolled=2"
            "&degreeID=0&grantTypeID=0&professionTypeID=0&centerTrainingDirectionsID=0"
            "&differentiatedGrant=0"
        )
        page.goto(search_url, wait_until="networkidle")

        # Ищем строку с единственным студентом
        rows = page.locator("tr[ng-repeat='student in vm.students']")
        count = rows.count()

        if count == 0:
            browser.close()
            raise RuntimeError("Не найден ни один студент с таким ИИН.")
        if count > 1:
            browser.close()
            raise RuntimeError("Найдено несколько студентов с таким ИИН.")

        row = rows.nth(0)

        # Ссылка на детальную страницу и ФИО
        link = row.locator("a[ng-href^='template.html#/student/']")
        fio = link.inner_text().strip()
        href = link.get_attribute("href") or link.get_attribute("ng-href")

        student_id: Optional[str] = None
        if href:
            parts = href.split("/")
            if parts:
                candidate = parts[-1]
                if "#" in candidate:
                    candidate = candidate.split("#")[-1]
                if candidate.isdigit():
                    student_id = candidate

        # Остальные колонки строки (форма обучения, код и т.п.)
        cells = row.locator("td")
        cells_count = cells.count()
        row_data: List[str] = []
        for idx in range(cells_count):
            row_data.append(cells.nth(idx).inner_text().strip())

        # Переходим на детальную страницу и даём ей догрузиться
        link.click()
        page.wait_for_load_state("networkidle")
        try:
            # ждём появления селекта с курсом (примерно то, что ты присылал)
            page.wait_for_selector("select[name='courseNumber']", timeout=5000)
        except TimeoutError:
            # если конкретный селектор не появился, всё равно берём HTML
            pass

        detail_html = page.content()

        page.goto("https://platonus.tau-edu.kz/messageedit?type=1&state=2")

        try:
            page.wait_for_selector("#theme", timeout=10000)
            page.fill("#theme", "Test Notification")
            page.wait_for_selector(".note-editable")
            page.evaluate(f"""
            $('#summernote').summernote('code', 'Test Notification code {code}');
            """)
        except TimeoutError as exc:
            browser.close()
            raise RuntimeError(
                "Не удалось найти поля для создания уведомления на странице."
            ) from exc

        page.wait_for_selector('input[name="send"]')
        page.click('input[name="send"]')
        # page.wait_for_load_state("networkidle")

        page.wait_for_selector('input[name="search"]')
        page.fill('input[name="search"]', fio)
        page.click('button[name="find"]')

        page.wait_for_selector(f'input[name="to{student_id}"]', timeout=10000)
        page.check(f'input[name="to{student_id}"]')

        page.wait_for_selector('input[name="send"]', timeout=10000)
        page.click('input[name="send"]')


        detail_html = page.content()
        browser.close()

        return {
            "html": detail_html,
            "iin": iin,
            "fio": fio,
            "student_id": student_id,
            "row": row_data,
        }


if __name__ == "__main__":
    env_username = os.getenv("PLATONUS_USERNAME")
    env_password = os.getenv("PLATONUS_PASSWORD")
    env_iin = os.getenv("PLATONUS_IIN")

    if not env_username or not env_password or not env_iin:
        raise SystemExit(
            "Environment variables PLATONUS_USERNAME, PLATONUS_PASSWORD and PLATONUS_IIN must be set."
        )

    content = fetch_notifications(env_username, env_password, env_iin)
    print(content)

