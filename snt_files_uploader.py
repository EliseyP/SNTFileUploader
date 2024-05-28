import configparser
import os
from datetime import datetime
# import inspect
import logging
from logging import Logger
# import time
from configparser import ExtendedInterpolation
from pathlib import Path
# from shutil import make_archive
from typing import Optional
from zipfile import ZipFile

import requests

basename = "snt_files_uploader"

config_ini_name = f"config.ini"
ini_file = Path(__file__).resolve().parent.joinpath(config_ini_name).as_posix()
emails_list_name = 'emails_list.csv'
emails_list_file = Path(__file__).resolve().parent.joinpath(emails_list_name).as_posix()


class UploaderApp:
    def __init__(self):
        self.settings: Optional[Settings] = None
        self.dirs_files: Optional[DirsFiles] = None
        self.logger_app: Optional[Logger] = None
        self.logger_sent: Optional[Logger] = None

    def __repr__(self):
        return f"{self.__class__.__qualname__}"

    def __str__(self):
        return f"{self.__class__.__name__}"

    def archive_sent_file(self, sent_file_path: Path):
        """Архивирование файла с данными.

        :param sent_file_path: Путь к файлу с данными.
        :type sent_file_path: Path
        :return:
        :rtype:
        """
        mtime: float = sent_file_path.stat().st_mtime
        dt = datetime.fromtimestamp(mtime)
        mtime_str = dt.strftime('%Y%m%d_%H%M%S_%f')
        archive_file_name = f'{mtime_str}.zip'
        archive_file_path = self.dirs_files.sent_dir.joinpath(archive_file_name)
        # make_archive('/path/to/folder', '/path/to/folder.zip')
        try:
            os.chdir(sent_file_path.parent)
        except OSError as e:
            self.logger_app.error(f'Error changing directory: "{sent_file_path.parent}".')
            return None
        try:
            with ZipFile(archive_file_path, "w") as myzip:
                myzip.write(sent_file_path.name)
        except Exception as e:
            self.logger_app.error(f'Erorr archiving file: "{sent_file_path}".')
            return None
        else:
            self.logger_app.debug(f'File "{sent_file_path.name}" archived to "{archive_file_path.name}"')
            return archive_file_path

    def send_email(self, sent_file_path: Path):
        """Рассылка показаний счетчика.

        :param sent_file_path:  Путь к файлу с данными.
        :type sent_file_path:  Path
        :return:
        :rtype:
        """
        return False

    def upload_file_to_server(self, file_path: Path):
        """Загрузить файл на сервер.

        :param file_path:
        :type file_path:
        :return:
        :rtype:
        """

        if not file_path or not file_path.exists():
            raise FileNotFoundError(f'No file "{file_path}"!')

        """
        HTTPSConnectionPool(host='el.sntch.ru', port=443): 
        Max retries exceeded with url: /import_meter_data.php 
        (Caused by SSLError(CertificateError("hostname 'el.sntch.ru' 
        doesn't match either of '*.timeweb.ru', 'timeweb.ru'")))
        """

        file_name = file_path.name
        with open(file_path, 'rb') as f:
            try:
                response = requests.post(settings.url_for_upload, files={file_name: f}, verify=False)
                # except requests.exceptions.HTTPError as e:
                # except requests.exceptions.ConnectTimeout as e:
                # except requests.exceptions.ConnectionError as e:
            except requests.exceptions.RequestException as e:
                self.logger_app.error(f'{e}')
                return False

        if 200 <= response.status_code < 300:
            return True
        else:
            self.logger_app.error(f'Error uploading file: "{file_path}". Code={response.status_code}.')
            return False

    def upload_several_files_to_server(self):
        """Загрузить все файлы из каталога watched_dir на сервер.

        После загрузки файл данных архивируется, удаляется.
        При необходимости файл/отчет посылается на почту.
        :return:
        :rtype:
        """
        self.logger_app.info(f'Start data files uploading.')
        try:
            files_list = self.get_files_from_watched_dir()
        except OSError:
            return
        if not files_list:
            self.logger_app.info(f'STOP data files uploading. No files for uploading.')
            return

        def process_one_file(_file: Path):
            upload_result = self.upload_file_to_server(_file)
            sent_log_string = f'File "{_file.name}" uploaded.'
            if not upload_result:
                self.logger_app.error(f'Upload error for file: "{_file}".')
                return None
            else:
                self.logger_app.debug(f'File uploaded: "{_file}"')

            archive_result = self.archive_sent_file(_file)
            if archive_result:
                try:
                    _file.unlink()
                except OSError as e:
                    self.logger_app.error(f'Error deleting file: "{_file}"')
                    return None
                else:
                    sent_log_string = sent_log_string[:-1] + f' and archived to "{archive_result.name}".'
                    self.logger_app.debug(f'File deleted: "{_file}"')
            else:
                self.logger_app.error(f'Archive error for file: "{_file}"')
                return None

            if self.settings.is_sent_logging:
                self.logger_sent.info(sent_log_string)

            if self.settings.is_send_emails:
                email_result = self.send_email(_file)
                if email_result:
                    self.logger_app.info(f'Email sent for file: "{_file}"')
                else:
                    self.logger_app.error(f'Email sent error for file: "{_file}"')
                    return None

        for data_file in files_list:
            process_one_file(data_file)

        self.logger_app.info(f'STOP data files uploading.')

    def get_files_from_watched_dir(self):
        """Получить список файлов с показаниями.

        :return:
        :rtype:
        """
        _files_list = []
        files_dir: Path = self.dirs_files.watched_dir
        for _file in files_dir.iterdir():
            if _file.suffix == '.csv':
                _files_list.append(_file)

        return _files_list


class Settings:
    """Настройки.

    """
    def __init__(self, _ini_file: str = None):
        self.root_data_dir = None
        self.watched_dir = None
        self.sent_dir = None
        self.log_dir = None
        self.log_file = None
        self.url_for_upload = None
        self.is_sent_logging = False
        self.is_archive_sent_files = False
        self.is_send_emails = False
        self.smtp_server = None
        self.app_log_level = None

        if not ini_file or not Path(ini_file).exists():
            raise FileNotFoundError(f"No ini file: {ini_file}")

        config = configparser.ConfigParser(interpolation=ExtendedInterpolation())
        config.read(ini_file)

        _url_for_upload = config.get("URLS", "url_for_upload")
        if _url_for_upload:
            self.url_for_upload = _url_for_upload

        _root_data_dir = config.get("DIRS", "root_data_dir")
        if _root_data_dir:
            self.root_data_dir = _root_data_dir

        _watched_dir = config.get("DIRS", "watched_dir")
        if _watched_dir:
            self.watched_dir = _watched_dir

        _sent_dir = config.get("DIRS", "sent_dir")
        if _sent_dir:
            self.sent_dir = _sent_dir

        _log_dir = config.get("DIRS", "log_dir")
        if _log_dir:
            self.log_dir = _log_dir

        _log_file = config.get("FILES", "log_file")
        if _log_file:
            self.log_file = _log_file

        _is_sent_logging = config.getboolean("LOG", "is_sent_logging")
        if _is_sent_logging:
            self.is_sent_logging = _is_sent_logging

        _is_archive_sent_files = config.getboolean("ARCHIVING", "is_archive_sent_files")
        if _is_archive_sent_files:
            self.is_archive_sent_files = _is_archive_sent_files

        _app_log_level = config.get("LOGLEVEL", "app_log_level")
        if _app_log_level:
            self.app_log_level = _app_log_level

        _is_send_emails = config.getboolean("EMAIL", "is_send_emails")
        if _is_send_emails:
            self.is_send_emails = _is_send_emails

        _smtp_server = config.get("EMAIL", "smtp_server")
        if _smtp_server:
            self.smtp_server = _smtp_server

    def __repr__(self):
        return f"{self.__class__.__qualname__}"

    def __str__(self):
        return f"{self.__class__.__name__}"


class DirsFiles:
    """Каталоги и файлы.

    """
    def __init__(self, _settings: Settings = None):
        self.root_dir = None
        self.watched_dir = None
        self.sent_dir = None
        self.log_dir = None
        self.log_file = None

        if not _settings:
            raise ValueError("No settings")

        self.root_dir = Path(_settings.root_data_dir)
        self.watched_dir = self.root_dir.joinpath(_settings.watched_dir)
        self.sent_dir = self.root_dir.joinpath(_settings.sent_dir)
        self.log_dir = self.root_dir.joinpath(_settings.log_dir)
        self.log_file = self.log_dir.joinpath(_settings.log_file)

        dirs_list = [self.root_dir, self.watched_dir,]
        if _settings.is_archive_sent_files:
            dirs_list.append(self.sent_dir)
        if _settings.is_sent_logging:
            dirs_list.append(self.log_dir)

        for _dir in dirs_list:
            if not _dir.exists():
                logging.debug(f'Directory "{_dir}"  not found!')
                try:
                    _dir.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    raise e
                else:
                    logging.debug(f'Directory "{_dir}"  created!')

    def __str__(self):
        return f"{self.__class__.__name__}"

    def __repr__(self):
        return f"{self.__class__.__qualname__}"


if __name__ == "__main__":
    settings = Settings(ini_file)
    _log_level = logging.INFO if settings.app_log_level == 'INFO' else logging.DEBUG

    dirs_files = DirsFiles(settings)

    def setup_logger(logger_name, log_file, level=logging.INFO, format_string=None):
        logger_obj = logging.getLogger(logger_name)
        if format_string:
            formatter = logging.Formatter(format_string)
        else:
            formatter = logging.Formatter('%(levelname)-9s %(asctime)s - %(message)s')
        # fileHandler = logging.FileHandler(log_file, mode='w')
        fileHandler = logging.FileHandler(log_file)
        fileHandler.setFormatter(formatter)
        streamHandler = logging.StreamHandler()
        streamHandler.setFormatter(formatter)

        logger_obj.setLevel(level)
        logger_obj.addHandler(fileHandler)
        logger_obj.addHandler(streamHandler)

    # Журнал приложения.
    setup_logger(logger_name='log_app',
                 log_file=f'{basename}.log',
                 level=_log_level)
    logger_app = logging.getLogger('log_app')

    # Журнал загрузки на сервер (и архивирования).
    setup_logger(logger_name='log_sent',
                 log_file=dirs_files.log_file,
                 format_string='%(asctime)s - %(message)s')
    logger_sent = logger_app
    if settings.is_sent_logging:
        logger_sent = logging.getLogger('log_sent')

    app = UploaderApp()
    app.settings = settings
    app.dirs_files = dirs_files
    app.logger_app = logger_app
    app.logger_sent = logger_sent

    app.upload_several_files_to_server()

    # Вариант с отслеживанием событий изменений файловой системы.
    # app.start_watching()
