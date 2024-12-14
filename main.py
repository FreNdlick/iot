import os
import threading
import datetime
from time import sleep

import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.card import MDCard
from kivy.lang import Builder
import tkinter as tk
from tkinter import messagebox, Listbox, Button, Label
from Parse_Mongo_data import parse_and_plot_mongodb_data
from mongo import init_db
from metricsPromet import create_sensor_metrics
from mqqt import start_mqtt_client
from app import start_http_server

load_dotenv()

KV = '''
MDScreen:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(20)

        MDLabel:
            text: "Мониторинг системы"
            halign: "center"
            theme_text_color: "Primary"
            font_style: "H4"
            bold: True

        MDCard:
            orientation: 'vertical'
            padding: dp(20)
            size_hint: None, None
            size: "280dp", "180dp"
            pos_hint: {"center_x": .5}

            BoxLayout:
                orientation: 'vertical'
                spacing: dp(10)

                MDLabel:
                    id: status_label
                    text: "Состояние: Нажмите кнопку подключения"
                    theme_text_color: "Secondary"
                    halign: "center"

                MDProgressBar:
                    id: progress_bar
                    value: 0
                    color: app.theme_cls.primary_color
                    type: "indeterminate"

                MDRaisedButton:
                    text: "Подключение"
                    icon: "server-network"
                    pos_hint: {"center_x": .5}
                    on_release: app.connect_to_server()

        MDCard:
            orientation: 'vertical'
            padding: dp(20)
            size_hint: None, None
            size: "280dp", "180dp"
            pos_hint: {"center_x": .5}

            BoxLayout:
                orientation: 'vertical'
                spacing: dp(10)

                MDLabel:
                    id: data_label
                    text: "Построение графиков из БД"
                    theme_text_color: "Primary"
                    halign: "center"


                MDRaisedButton:
                    text: "Выбрать датчик и дату"
                    icon: "calendar"
                    pos_hint: {"center_x": .5}
                    on_release: app.open_date_selection()
'''

class MainApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Dark"
        return Builder.load_string(KV)

    def connect_to_server(self):
        self.root.ids.progress_bar.value = 0
        self.root.ids.status_label.text = "Подключение к серверу..."
        for i in range(4):
            self.root.ids.progress_bar.value +=25
            sleep(0.02)
        threading.Thread(target=self.run_connection).start()
        self.root.ids.status_label.text = "Подключено к серверу"

    def run_connection(self):
        try:
            mongo_url = os.getenv("MONGO_URL")
            mongo_db = os.getenv("MONGO_DB")
            collection = init_db(mongo_url, mongo_db)

            start_http_server(8000)

            mqtt_broker_address = os.getenv("MQTT_BROKER_ADDRESS")
            mqtt_broker_port = int(os.getenv("MQTT_BROKER_PORT"))
            mqtt_topics = os.getenv("MQTT_TOPICS").split(',')

            sensor_metrics = {
                "000DE0163B57": create_sensor_metrics("000DE0163B57"),
                "000DE0163B59": create_sensor_metrics("000DE0163B59"),
                "000DE0163B58": create_sensor_metrics("000DE0163B58"),
                "000DE0163B56": create_sensor_metrics("000DE0163B56")
            }

            start_mqtt_client(mqtt_broker_address, mqtt_broker_port, mqtt_topics, collection, sensor_metrics)

            self.update_ui_on_connection_success()

        except Exception as e:
            self.update_ui_on_connection_failure(str(e))

    def update_ui_on_connection_success(self):
        self.root.ids.status_label.text = "Подключено к серверу!"
        self.root.ids.progress_bar.value = 100
        self.root.ids.sensor_data.text = "Получены данные от датчиков"

    def update_ui_on_connection_failure(self, error_message):
        self.root.ids.status_label.text = f"Ошибка подключения: {error_message}"
        self.root.ids.progress_bar.value = 0
        self.root.ids.sensor_data.text = "Данные не получены"

    def open_date_selection(self):
        self.date_selection_window = DateSelectionWindow(self)
        self.date_selection_window.mainloop()

class DateSelectionWindow(tk.Tk):
    def __init__(self, main_app):
        super().__init__()
        self.title("Выбор датчика и даты")
        self.geometry("300x400")
        self.main_app = main_app


        self.sensor_metrics = [
            "000DE0163B57",
            "000DE0163B59",
            "000DE0163B58",
            "000DE0163B56"
        ]
        self.selected_sensor = tk.StringVar(value=self.sensor_metrics[0])
        Label(self, text="Выберите датчик:").pack()

        self.sensor_menu = tk.OptionMenu(self, self.selected_sensor, *self.sensor_metrics)
        self.sensor_menu.pack()

        Button(self, text="Загрузить даты", command=self.load_dates).pack()

        self.listbox = Listbox(self)
        self.listbox.pack()

        Button(self, text="Построить график", command=self.plot_selected_date).pack()

    def load_dates(self):
        database_name = "mqtt_database"
        collection_name = "your_collection"

        self.df = parse_and_plot_mongodb_data(database_name, collection_name, self.selected_sensor.get())

        if self.df.empty:
            self.listbox.delete(0, tk.END)
            self.listbox.insert(tk.END, "Ошибка при получении данных")
        else:
            self.dates = sorted(self.df['MsgTimeStamp'].dt.date.unique().tolist())
            self.listbox.delete(0, tk.END)
            for date in self.dates:
                self.listbox.insert(tk.END, date.strftime("%Y-%m-%d"))

    def plot_selected_date(self):
        selected_index = self.listbox.curselection()
        if not selected_index:
            messagebox.showwarning("Предупреждение", "Пожалуйста, выберите дату.")
            return

        selected_date = self.dates[selected_index[0]]
        filtered_df = self.df[self.df['MsgTimeStamp'].dt.date == selected_date]

        if filtered_df.empty:
            messagebox.showwarning("Предупреждение", "Нет данных для выбранной даты.")
            return

        plt.figure(figsize=(14, 10))
        # График Humidity по времени
        plt.subplot(3, 2, 1)
        plt.plot(filtered_df['MsgTimeStamp'], filtered_df['Humidity'], label='Humidity', color='blue')
        plt.xlabel("Время")
        plt.ylabel("Humidity")
        plt.title(f"Humidity за {selected_date}")
        plt.grid(True)
        plt.xticks(rotation=45)

        # График TemperatureC по времени
        plt.subplot(3, 2, 2)
        plt.plot(filtered_df['MsgTimeStamp'], filtered_df['TemperatureC'], label='TemperatureC', color='red')
        plt.xlabel("Время")
        plt.ylabel("TemperatureC")
        plt.title(f"TemperatureC за {selected_date}")
        plt.grid(True)
        plt.xticks(rotation=45)

        # График TemperatureF по времени
        plt.subplot(3, 2, 3)
        plt.plot(filtered_df['MsgTimeStamp'], filtered_df['TemperatureF'], label='TemperatureF', color='green')
        plt.xlabel("Время")
        plt.ylabel("TemperatureF")
        plt.title(f"TemperatureF за {selected_date}")
        plt.grid(True)
        plt.xticks(rotation=45)

        # График DewPointC по времени
        plt.subplot(3, 2, 4)
        plt.plot(filtered_df['MsgTimeStamp'], filtered_df['DewPointC'], label='DewPointC', color='orange')
        plt.xlabel("Время")
        plt.ylabel("DewPointC")
        plt.title(f"DewPointC за {selected_date}")
        plt.grid(True)
        plt.xticks(rotation=45)

        # График DewPointF по времени
        plt.subplot(3, 2, 5)
        plt.plot(filtered_df['MsgTimeStamp'], filtered_df['DewPointF'], label='DewPointF', color='purple')
        plt.xlabel("Время")
        plt.ylabel("DewPointF")
        plt.title(f"DewPointF за {selected_date}")
        plt.grid(True)
        plt.xticks(rotation=45)

        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    MainApp().run()