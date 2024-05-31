"""
EmailsListReader.py
Получение информации из списка почтовых адресов для рассылки отчетов.

Список находится в файле emails_list.csv.
NN,email_1,email_2,...
Заголовка в csv-файле нет.
Количество столбцов переменное.
"""
import csv
import logging
from logging import Logger
from pathlib import Path
from typing import Union

from email_validator import validate_email, EmailNotValidError


class EmailsListReader:
    """Объект этого класса создает словарь данных из списка адресов рассылки для каждого участка.

    Главный атрибут: словарь csv_dict, который отражает список адресов рассылки.
    Адреса проходят проверку на корректность и на возможность доставки.
    Некорректные адреса отбрасываются (с занесением в журнал).
    """

    def __init__(self, csv_file: Union[str, Path], app_logger: Logger = None):
        if not csv_file or not Path(csv_file).exists():
            raise ValueError(f'File "{csv_file}" is not exists!')
        self.csv_file = Path(csv_file)
        self.csv_dict = self.get_all_data_dict_from_csv()
        self.log = app_logger if app_logger else logging
        self.validate_all_email_addresses()

    def __str__(self):
        return f"{self.__class__.__name__}"

    def __repr__(self):
        return f"{self.__class__.__qualname__}({self.csv_file.name})"

    def get_all_data_dict_from_csv(self):
        _csv_dict = {}
        with open(self.csv_file, "r", encoding="utf-8") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",", skipinitialspace=True)
            for row in csv_reader:
                _garden_number = row[0].strip()
                address_list = row[1:]
                _csv_dict[_garden_number] = address_list
        return _csv_dict

    def validate_all_email_addresses(self):
        """Проверка адресов на наличие, корректность и на возможность доставки.

        Некорректные адреса удаляются из словаря self.csv_dict.
        Отладочные сообщения закомментированы (в журнал)
        :return:
        :rtype:
        """
        self.log.debug('Проверка адресов на корректность и на возможность доставки.')
        for _garden_number, address_list in self.csv_dict.items():
            # Если в строке только номер участка.
            if not address_list:
                self.log.warning(f'Проверка: Участок {_garden_number}: не указаны адреса!')
                continue

            _address_list = []
            for address in address_list:
                _address = address.strip()

                # Если пустое значение (стоит только одна запятая).
                if _address == '':
                    self.log.warning(f'Проверка: Участок {_garden_number}: не указаны адреса (стоит одна запятая)!')
                    continue

                validation_error = check_email(_address, check_deliverability=True)
                if validation_error:
                    self.log.error(f'Проверка: Участок "{_garden_number}": Ошибка в адресе "{_address}": {str(validation_error)}')
                else:
                    _address_list.append(_address)
            self.csv_dict[_garden_number] = _address_list

        self.log.debug('Проверка окончена.')

    def get_addreses_list_for_garden_number(self, _garden_number: Union[int, str]):
        return self.csv_dict.get(str(_garden_number))

    def get_garden_numbers_list(self):
        return list(self.csv_dict.keys())

    def process_data_from_csv(self):
        """Заготовка. Вывод данных на экран.

        """
        for _garden_number, address_list in self.csv_dict.items():
            if address_list:
                print(f'Участок: "{_garden_number}", Адреса:{",".join(address_list)}')
                for address in address_list:
                    print(f"{_garden_number} - {address}")
            else:
                print(f'Участок "{_garden_number}": адресов нет.')


def check_email(email: str, check_deliverability: bool = False) -> Union[str, None]:
    """Проверка адреса на корректрность и возможность доставки.

    При положительном результате проверки возвращается None.
    При отрицательном результате проверки возвращается строка с описанием ошибки.
    :param email:
    :type email:
    :param check_deliverability: Проверка возможность доставки.
    :type check_deliverability: bool.
    :return:
    :rtype:
    """
    try:
        # Check that the email address is valid. Turn on check_deliverability
        # for first-time validations like on account creation pages (but not
        # login pages).
        validate_email(email, check_deliverability=check_deliverability)
        return None
    except EmailNotValidError as err:
        # The exception message is human-readable explanation of why it's
        # not a valid (or deliverable) email address.
        return str(err)


def get_checked_email(email, check_deliverability: bool = False):
    try:
        # Check that the email address is valid. Turn on check_deliverability
        # for first-time validations like on account creation pages (but not
        # login pages).
        emailinfo = validate_email(email, check_deliverability=check_deliverability)

        # After this point, use only the normalized form of the email address,
        # especially before going to a database query.
        _email = emailinfo.normalized
        return _email
    except EmailNotValidError as err:
        # The exception message is human-readable explanation of why it's
        # not a valid (or deliverable) email address.
        print(f'Ошибка в адресе "{email}": {str(err)}')


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)-9s %(asctime)s - %(message)s')
    try:
        email_reader = EmailsListReader("emails_list.csv")
    except ValueError as e:
        print(f'Error: {e}')
        exit()

    # Заготовка 1. Операции над всем словарем (вывод данныъ).
    email_reader.process_data_from_csv()

    # Заготовка 2. Список номеров участков.
    garden_numbers_list = email_reader.get_garden_numbers_list()
    print(f'Участки: {",".join(garden_numbers_list)}.')

    # Заготовка 3. Отдельный участок.
    garden_number = '100'
    if garden_number in garden_numbers_list:
        addreses_list = email_reader.get_addreses_list_for_garden_number(garden_number)
        if addreses_list:
            print(f'Адреса участка "{garden_number}": {",".join(addreses_list)}')
        else:
            print(f'Участок "{garden_number}": адресов нет.')
    else:
        print(f'Участок "{garden_number}" не найден.')
