# SNTFileUploader
Uploader csv files to webserver

**version = 0.0.3**

Структура каталогов на компьютере-агрегаторе, принимающем данные со счетчиков:  

**root_data_dir**  
&nbsp;&nbsp;|-> **watched_dir**  (файлы показаний)  
&nbsp;&nbsp;|-> **sent_dir**  (архивные копии)  
&nbsp;&nbsp;|-> **log_dir** (файл журнал загрузки)    

## Основные операции:
- Файлы с данными от счетчиков уже загружены в каталог **watched_dir.**
- Все файлы загружается на сервер.
- Архивированные копии перемещаются в каталог **sent_dir.**  
- В журнал `log_dir/log_file` заносится запись о загрузке (и архивировании).  

***  

**Формат имени файла данных:**  
`*.csv`  
`Авто_Гр_ver.7_показ_2024-05-27_11_10.csv`

**Формат имени файла архивированной копии:**  
`YYYYMMDD_hhmmss_[microseconds].zip`  
`20240528_011825_601307.zip`


**Формат записи в журнал:**  
`YYYY-MM-DD_hh_mm_ssss: File "*.csv" uploaded and archived to "YYYYMMDD_hhmmss_[microseconds].zip"`  
`2024-05-28 03:09:43,816 - File "Авто_Гр_ver.7_показ_2024-05-27_11_10.csv" uploaded and archived to "20240528_011819_673413.zip".`

***

Скрипт рассчитан на запуск через планировщик.  
Работает и на Linux.

***
Для работы скрипта необходимо установить python-модуль `requests`.

***
Конфигурационный файл: `config.ini`.  
Необходимые параметры: 
- путь к каталогу `root_data_dir`.  
- url сервера загрузки `url_for_upload`.

Предусмотрены два журнала: 
- для самого приложения (можно указать уровень вывода информации `DEBUG|INFO`). Файл журнала по умолчанию находится в том же каталоге, где и сам скрипт. С тем же названием `snt_files_uploader.log`. Каталог размещения можно указать в настройках.
- для непосредственно операций загрузки (и архивирования). Файл журнала находится в каталоге `root_data_dir/log/snt_upload.log`.
 
