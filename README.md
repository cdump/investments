# Investments
Библиотека для анализа брокерских отчетов + утилиты для подготовки налоговой отчетности

![Tests status](https://github.com/cdump/investments/workflows/tests/badge.svg)

## Установка/обновление
```
$ pip3 install investments --upgrade --user
```
или с помощью [poetry](https://python-poetry.org/)

## Утилита ibtax
Расчет прибыли Interactive Brokers для уплаты налогов для резидентов РФ

- расчет сделок по методу ФИФО, учет даты расчетов (settle date)
- конвертация по курсу ЦБ
- поддержка валют USD, RUB, EUR, AUD, GBP, CAD, CZK, DKK, HKD, HUF, YEN, KRW, NOK, PLN, SGD, ZAR, SEK, CHF, TRY
- раздельный результат сделок по акциям и опционам + дивиденды
- учёт начисленных процентов на остаток по счету
- учёт комисий по сделкам
- пока **НЕ** поддерживаются валюты CNH, ILS, MXN, NZD
- пока **НЕ** поддерживаются сплиты
- пока **НЕ** поддерживаются сделки Forex, сделка пропускается и выводится сообщение о том, что это может повлиять на итоговый отчет

*Пример отчета:*
![ibtax report example](./images/ibtax_2020.jpg)

### Запуск
```
$ python3 -m investments.ibtax --activity-reports-dir /path/to/activity/dir --confirmation-reports-dir /path/to/confirmation/dir
```
Отчеты `activity` & `confirmation` должны:
- быть выгружены из IB в формате CSV
- лежать в разных директориях (см. *Подготовка отчетов Interactive Brokers*)

#### Просмотр неокруглённых цифр в расчётах
```
$ python3 -m investments.ibtax --verbose --activity-reports-dir /path/to/activity/dir --confirmation-reports-dir /path/to/confirmation/dir
```

#### Экпорт отчёта в pdf файл
```
$ python3 -m investments.ibtax --save-to /path/to/ibtax-report.pdf --activity-reports-dir /path/to/activity/dir --confirmation-reports-dir /path/to/confirmation/dir
```


## Утилита ibdds
Утилита для подготовки отчёта о движении денежных средств по счетам у брокера Interactive Brokers (USA) для резидентов РФ

- выводит отчёт по каждой валюте счёта отдельно
- вывод максимально приближен к форме отчёта о ДДС

*Пример отчета:*
![ibdds report example](./images/ibdds_2020.png)

### Запуск
```
$ python3 -m investments.ibdds --activity-report-filepath /path/to/activity/report.csv
```
Отчет `activity` должен:
- быть выгружен из IB в формате CSV
- отражать активность за один год (см. *Подготовка отчетов Interactive Brokers*)


## Подготовка отчетов Interactive Brokers
Для работы нужно выгрузить из [личного кабинета](https://www.interactivebrokers.co.uk/sso/Login) два типа отчетов: *Activity statement* (сделки, дивиденды, информация по инструментам и т.п.) и *Trade Confirmation* (settlement date, необходимая для правильной конвертации сумм по курсу ЦБ)

Отчёты должны быть названы так, чтобы сортировались естественным образом по годам начиная от старого к новому. Такого можно достичь называя файлик номером года (например 2019.csv).

### Activity statement
Для загрузки нужно перейти в **Reports / Tax Docs** > **Default Statements** > **Activity**

Выбрать `Format: CSV` и скачать данные за все доступное время (`Perioid: Annual` для прошлых лет + `Period: Year to Date` для текущего года)

**Обязательно выгрузите отчеты за все время существования вашего счета!**

![Activity Statement](./images/ib_report_activity.jpg)

### Trade Confirmation

Для загрузки нужно перейти в **Reports / Tax Docs** > **Flex Queries** > **Trade Confirmation Flex Query** и создать новый тип отчетов, выбрав в **Sections** > **Trade Confirmation** все пункты в группе **Executions**, остальные настройки - как на скриншоте:

![Trade Confirmation Flex Query](./images/ib_trade_confirmation_settings.jpg)

После этого в **Reports / Tax Docs** > **Custom Statements** выгрузите отчеты **за все время существования вашего счета**, используя `Custom date range` периодами по 1 году (больше IB поставить не дает):


![Trade Confirmation Statement](./images/ib_report_trade_confirmation.jpg)


## Разворачивание проекта для внесения изменений

- Install [poetry](https://python-poetry.org/docs/#installation)
- Clone & modify & run

```
$ git clone https://github.com/cdump/investments

$ cd investments

$ poetry install
$ poetry run ibtax
usage: ibtax [-h] --activity-reports-dir ACTIVITY_REPORTS_DIR --confirmation-reports-dir CONFIRMATION_REPORTS_DIR [--cache-dir CACHE_DIR] [--years YEARS] [--verbose]
ibtax: error: the following arguments are required: --activity-reports-dir, --confirmation-reports-dir

$ vim investments/ibtax/ibtax.py # edit main file for example

$ poetry run ibtax # run updated version
```
