import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta


load_dotenv()


BASE_URL = "http://air.krasn.ru/api/2.0"

def get_projects():
    url = f"{BASE_URL}/projects"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def get_project_info(project_id):
    url = f"{BASE_URL}/projects/{project_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def get_data(time_begin, time_end, time_interval="hour", sites="3837"):
    url = f"{BASE_URL}/data"
    params = {
        "time_begin": time_begin,
        "time_end": time_end,
        "time_interval": time_interval,
        "sites": sites
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def main():
    try:
        # Получить список проектов
        projects = get_projects()
        print("Список проектов:")
        print(projects)

        # Проверка, является ли projects списком и содержит ли он элементы
        if isinstance(projects, list) and projects:
            first_project = projects[0]
            if isinstance(first_project, dict) and 'id' in first_project:
                first_project_id = first_project['id']
                project_info = get_project_info(first_project_id)
                print(f"\nИнформация о проекте {first_project_id}:")
                print(project_info)
            else:
                print("\nСтруктура данных проекта не соответствует ожидаемой.")
        else:
            print("\nСписок проектов пуст или имеет неожиданный формат.")

        # Получить данные за последние 24 часа
        now = datetime.now()
        time_end = now.strftime("%Y-%m-%d %H:%M:%S")
        time_begin = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

        data = get_data(time_begin, time_end)
        print("\nДанные за последние 24 часа:")
        print(data)

    except requests.RequestException as e:
        print(f"Произошла ошибка при выполнении запроса: {e}")
    except Exception as e:
        print(f"Произошла неожиданная ошибка: {e}")


if __name__ == "__main__":
    main()