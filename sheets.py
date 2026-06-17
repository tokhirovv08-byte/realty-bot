import os
import json
import tempfile
import gspread
from google.oauth2.service_account import Credentials
from config import SPREADSHEET_ID

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

HEADERS = ['ID', 'Район', 'Локация', 'Площадь (м²)', 'Комнат',
           'Этаж', 'Этажей в подъезде', 'Этажей в доме',
           'Мебель/техника', 'Ремонт', 'Цена ($)', 'Контакт',
           'Имя собственника', 'Телефон собственника', 'Фото']


class SheetsManager:
    def __init__(self):
        try:
            # Читаем credentials из переменной окружения (для Railway)
            # или из файла (для локального запуска)
            google_creds_json = os.environ.get('GOOGLE_CREDENTIALS')

            if google_creds_json:
                # Railway: из переменной окружения
                creds_dict = json.loads(google_creds_json)
                creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            else:
                # Локально: из файла credentials.json
                creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)

            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(SPREADSHEET_ID).sheet1
            self._ensure_headers()
            print("✅ Подключение к Google Sheets успешно!")
        except Exception as e:
            print(f"❌ Ошибка подключения к Google Sheets: {e}")
            self.sheet = None

    def _ensure_headers(self):
        try:
            first_row = self.sheet.row_values(1)
            if not first_row or first_row[0] != 'ID':
                self.sheet.insert_row(HEADERS, 1)
                self.sheet.format('A1:O1', {
                    'backgroundColor': {'red': 0.2, 'green': 0.5, 'blue': 0.9},
                    'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                    'horizontalAlignment': 'CENTER'
                })
        except Exception as e:
            print(f"Ошибка при создании заголовков: {e}")

    def _get_next_id(self):
        try:
            all_ids = self.sheet.col_values(1)[1:]
            if not all_ids:
                return 1
            numeric_ids = [int(x) for x in all_ids if str(x).isdigit()]
            return max(numeric_ids) + 1 if numeric_ids else 1
        except Exception:
            return 1

    def add_apartment(self, apt: dict) -> int:
        if not self.sheet:
            return -1
        apt_id = self._get_next_id()
        row = [
            apt_id,
            apt.get('district', ''),
            apt.get('location', ''),
            apt.get('area', ''),
            apt.get('rooms', ''),
            apt.get('floor', ''),
            apt.get('total_floors', ''),
            apt.get('building_floors', ''),
            apt.get('furniture', ''),
            apt.get('renovation', ''),
            apt.get('price', ''),
            apt.get('contact', ''),
            apt.get('owner_name', ''),
            apt.get('owner_phone', ''),
            apt.get('photos', ''),
        ]
        self.sheet.append_row(row, value_input_option='USER_ENTERED')
        return apt_id

    def get_all_apartments(self) -> list:
        if not self.sheet:
            return []
        try:
            records = self.sheet.get_all_records()
            return [self._record_to_apt(r) for r in records]
        except Exception as e:
            print(f"Ошибка получения данных: {e}")
            return []

    def search_apartments(self, filters: dict) -> list:
        all_apts = self.get_all_apartments()
        return [apt for apt in all_apts if self._matches(apt, filters)]

    def _matches(self, apt: dict, filters: dict) -> bool:
        district = filters.get('district')
        if district and district.lower() not in apt.get('district', '').lower():
            return False

        price_min = filters.get('price_min')
        if price_min is not None:
            try:
                if int(apt.get('price', 0)) < price_min:
                    return False
            except (ValueError, TypeError):
                pass

        price_max = filters.get('price_max')
        if price_max is not None:
            try:
                if int(apt.get('price', 999999)) > price_max:
                    return False
            except (ValueError, TypeError):
                pass

        rooms = filters.get('rooms')
        if rooms:
            if rooms == '4':
                try:
                    if int(apt.get('rooms', 0)) < 4:
                        return False
                except (ValueError, TypeError):
                    return False
            else:
                if str(apt.get('rooms', '')) != str(rooms):
                    return False

        furniture = filters.get('furniture')
        if furniture == 'да':
            if 'мебель' not in apt.get('furniture', '').lower():
                return False
        elif furniture == 'нет':
            if 'мебель' in apt.get('furniture', '').lower():
                return False

        renovation = filters.get('renovation')
        if renovation:
            if renovation.lower() not in apt.get('renovation', '').lower():
                return False

        return True

    def _record_to_apt(self, record: dict) -> dict:
        return {
            'id': record.get('ID', ''),
            'district': record.get('Район', ''),
            'location': record.get('Локация', ''),
            'area': record.get('Площадь (м²)', ''),
            'rooms': record.get('Комнат', ''),
            'floor': record.get('Этаж', ''),
            'total_floors': record.get('Этажей в подъезде', ''),
            'building_floors': record.get('Этажей в доме', ''),
            'furniture': record.get('Мебель/техника', ''),
            'renovation': record.get('Ремонт', ''),
            'price': record.get('Цена ($)', ''),
            'contact': record.get('Контакт', ''),
            'owner_name': record.get('Имя собственника', ''),
            'owner_phone': record.get('Телефон собственника', ''),
            'photos': record.get('Фото', ''),
        }
